from faststream.kafka import KafkaBroker
from core.config.kafka_config import kafka_config


# 전역 Kafka Broker 설정
# TODO: Producer 설정 (역방향 메시지 발행 시 추가 필요)
#   - acks=kafka_config.producer_acks
#   - compression_type=kafka_config.producer_compression_type
#   - 재시도: 앱 레벨(base_producer.py 지수 백오프 3회)만 사용,
#     Kafka 레벨 retries는 0으로 두어 중복 시도 방지
kafka_broker = KafkaBroker(
    bootstrap_servers=kafka_config.bootstrap_servers,
)
