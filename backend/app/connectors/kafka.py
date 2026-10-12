"""Kafka 连接器（不依赖 kafka-python）。

实现原理：用 socket 直接发送 Kafka 协议的 ApiVersionsRequest 与 MetadataRequest。
- test()：连第一个 broker，发 ApiVersions（v0），能解析响应即视作通
- list_topics()：发 Metadata（v1），自动列举 broker 上所有 topic

无认证 PLAINTEXT 元数据支持轻量协议；SASL/SSL 与消息采样使用 kafka-python。
"""
from __future__ import annotations

import socket
import struct


def _read_n(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Kafka broker 提前关闭连接")
        buf += chunk
    return buf


def _read_response(sock: socket.socket) -> bytes:
    size_bytes = _read_n(sock, 4)
    (size,) = struct.unpack(">i", size_bytes)
    if size <= 0 or size > 100_000_000:
        raise ValueError(f"Kafka 响应大小异常: {size}")
    return _read_n(sock, size)


def _send_request(sock: socket.socket, api_key: int, api_version: int,
                  client_id: str, body: bytes) -> bytes:
    cid = client_id.encode("utf-8")
    header = (
        struct.pack(">hhi", api_key, api_version, 1)
        + struct.pack(">h", len(cid)) + cid
    )
    payload = header + body
    sock.sendall(struct.pack(">i", len(payload)) + payload)
    return _read_response(sock)


def _parse_brokers(params: dict) -> list[tuple[str, int]]:
    raw = params.get("brokers") or params.get("host") or ""
    out: list[tuple[str, int]] = []
    for piece in (raw.split(",") if isinstance(raw, str) else raw):
        piece = piece.strip()
        if not piece:
            continue
        if ":" in piece:
            h, p = piece.rsplit(":", 1)
            out.append((h, int(p)))
        else:
            out.append((piece, int(params.get("port") or 9092)))
    return out


class KafkaConnector:
    category = "message_queue"
    type = "kafka"

    def sample_messages(self, *, params: dict, credential: dict | None, limit=20) -> list[dict]:
        """Read a bounded sample without committing or advancing a consumer group's offsets."""
        if not params.get("topic"):
            raise ValueError("消息采样需要 topic")
        if params["topic"] not in self.list_topics(params=params, credential=credential):
            raise ValueError("Kafka topic 不存在或无权访问")
        consumer = self._consumer(params, credential, params["topic"])
        try:
            messages = []
            for message in consumer:
                messages.append({"partition": message.partition, "offset": message.offset,
                                 "key": message.key.decode("utf-8", errors="replace") if message.key else None,
                                 "value": message.value.decode("utf-8", errors="replace"), "timestamp": message.timestamp})
                if len(messages) >= limit:
                    break
            return messages
        finally:
            consumer.close()

    def _consumer(self, params, credential, *topics):
        try:
            from kafka import KafkaConsumer
        except ImportError as exc:
            raise RuntimeError("Kafka 消息预览需要 kafka-python；请安装 backend/requirements.txt") from exc
        brokers = _parse_brokers(params)
        if not brokers:
            raise ValueError("缺少 Kafka broker")
        credential = credential or {}
        security = params.get("security_protocol") or ("SASL_PLAINTEXT" if credential else "PLAINTEXT")
        kwargs = {"bootstrap_servers": [f"{h}:{p}" for h, p in brokers], "group_id": None,
                  "enable_auto_commit": False, "allow_auto_create_topics": False,
                  "auto_offset_reset": "earliest", "consumer_timeout_ms": 3000,
                  "request_timeout_ms": 5000, "session_timeout_ms": 3000, "heartbeat_interval_ms": 1000,
                  "api_version_auto_timeout_ms": 3000, "security_protocol": security}
        for key in ("ssl_cafile", "ssl_certfile", "ssl_keyfile", "ssl_check_hostname"):
            if key in params:
                kwargs[key] = params[key]
        if credential:
            kwargs.update(sasl_mechanism=params.get("sasl_mechanism", "PLAIN"),
                          sasl_plain_username=credential.get("username"), sasl_plain_password=credential.get("password"))
        return KafkaConsumer(*topics, **kwargs)

    def _open(self, brokers: list[tuple[str, int]]) -> socket.socket:
        last_err: Exception | None = None
        for host, port in brokers:
            try:
                s = socket.create_connection((host, port), timeout=5)
                return s
            except Exception as e:
                last_err = e
        raise ConnectionError(f"所有 broker 不可达: {last_err}")

    def test(self, *, params: dict, credential: dict | None) -> tuple[bool, str]:
        if (params.get("security_protocol") or "PLAINTEXT").upper() != "PLAINTEXT" or credential:
            try:
                consumer = self._consumer(params, credential)
                try:
                    consumer.topics()
                    return True, "Kafka 认证连接成功"
                finally:
                    consumer.close()
            except Exception as exc:
                return False, f"Kafka 认证连接失败: {exc}"
        brokers = _parse_brokers(params)
        if not brokers:
            return False, "缺少 brokers 参数（host:port,host:port）"
        try:
            sock = self._open(brokers)
            try:
                # ApiVersionsRequest v0：空 body
                resp = _send_request(sock, api_key=18, api_version=0,
                                     client_id="ontology-probe", body=b"")
                if len(resp) < 6:
                    return False, "Kafka 响应过短"
                # 跳过 correlation_id (4) + error_code (2)；只要解到 error_code 即视为通
                (_corr, error_code) = struct.unpack(">ih", resp[:6])
                if error_code != 0:
                    return False, f"Kafka 协议错误码 {error_code}"
                return True, "连接成功"
            finally:
                sock.close()
        except Exception as e:
            return False, f"连接失败: {e}"

    def list_topics(self, *, params: dict, credential: dict | None) -> list[str]:
        if (params.get("security_protocol") or "PLAINTEXT").upper() != "PLAINTEXT" or credential:
            consumer = self._consumer(params, credential)
            try:
                return sorted(consumer.topics())
            finally:
                consumer.close()
        brokers = _parse_brokers(params)
        if not brokers:
            raise ValueError("缺少 brokers 参数")
        sock = self._open(brokers)
        try:
            # MetadataRequest v1，body = topics（int32=-1 表示全部）
            body = struct.pack(">i", -1)
            resp = _send_request(sock, api_key=3, api_version=1,
                                 client_id="ontology-probe", body=body)
            return _parse_metadata_topics(resp)
        finally:
            sock.close()


def _parse_metadata_topics(resp: bytes) -> list[str]:
    """粗暴但够用的 MetadataResponse v1 解析（只取 topic name 列表）。"""
    pos = 4  # correlation_id
    # brokers array
    (broker_n,) = struct.unpack_from(">i", resp, pos)
    pos += 4
    for _ in range(broker_n):
        # node_id i32, host: short-string, port i32, rack: nullable short-string
        pos += 4
        (host_len,) = struct.unpack_from(">h", resp, pos)
        pos += 2 + max(0, host_len)
        pos += 4
        (rack_len,) = struct.unpack_from(">h", resp, pos)
        pos += 2
        if rack_len > 0:
            pos += rack_len
    # controller_id i32
    pos += 4
    # topics array
    (topic_n,) = struct.unpack_from(">i", resp, pos)
    pos += 4
    out: list[str] = []
    for _ in range(topic_n):
        (err_code,) = struct.unpack_from(">h", resp, pos)
        pos += 2
        (name_len,) = struct.unpack_from(">h", resp, pos)
        pos += 2
        name = resp[pos:pos + name_len].decode("utf-8", errors="replace")
        pos += name_len
        # is_internal bool
        pos += 1
        # partitions array (跳过)
        (part_n,) = struct.unpack_from(">i", resp, pos)
        pos += 4
        for _ in range(part_n):
            # err_code i16, partition_id i32, leader i32
            pos += 2 + 4 + 4
            # replicas / isr arrays
            for _ in range(2):
                (n,) = struct.unpack_from(">i", resp, pos)
                pos += 4
                pos += 4 * n
        if err_code == 0:
            out.append(name)
    return out
