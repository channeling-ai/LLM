# YouTube 영상 분석 AI 시스템

## 📖 프로젝트 개요

YouTube 영상을 종합적으로 분석하여 크리에이터들에게 유용한 인사이트를 제공하는 AI 기반 분석 시스템입니다.

## 🎯 주요 기능

### 1. 개요 (Overview)
- **영상 평가 수치**: 조회수, 좋아요, 댓글 수 등 YouTube Analytics 기반 성과 지표 분석
- **댓글 분석**: 댓글을 감정별(긍정/부정/중립/조언)로 분류하고 요약 (최적화된 샘플링 적용)
- **영상 요약**: YouTube 자막을 분석하여 구간별 개요 생성

### 2. 분석 (Analysis)
- **시청자 이탈 분석**: YouTube Analytics 데이터로 시청자 이탈 지점 파악 및 원인 분석
- **알고리즘 최적화**: 제목, 설명, 태그 등 YouTube 알고리즘 최적화 방안 제시

### 3. 아이디어 (Idea)
- **트렌드 키워드**: 실시간 트렌드 + 채널 콘셉트 맞춤형 키워드 추천
- **콘텐츠 아이디어**: 분석 결과를 바탕으로 한 새로운 콘텐츠 아이디어 제안

## 🏗️ 시스템 아키텍처

- **Backend**: Python FastAPI + SQLModel
- **Database**: PostgreSQL (비즈니스 데이터 + 벡터 임베딩)
- **Message Queue**: Apache Kafka
- **AI/LLM**: OpenAI GPT-4o-mini
- **External APIs**: YouTube Data API v3, YouTube Analytics API

## 📁 프로젝트 구조

```
LLM/
├── domain/                 # 도메인 로직
│   ├── comment/           # 댓글 분석
│   ├── report/            # 보고서 생성
│   ├── video/             # 영상 정보
│   └── trend_keyword/     # 트렌드 키워드
├── external/              # 외부 서비스 연동
│   ├── rag/              # LLM 서비스
│   └── youtube/          # YouTube API
├── core/                  # 공통 설정
│   ├── config/           # 데이터베이스 설정
│   └── llm/              # 프롬프트 템플릿
└── kafka_consumer/        # Kafka 메시지 처리
```

## 🚀 주요 특징

- **비동기 처리**: Kafka를 통한 대용량 데이터 비동기 처리
- **성능 최적화**: 댓글 분석 시 샘플링 기법으로 80% 성능 향상
- **확장 가능성**: 마이크로서비스 아키텍처 기반 모듈화 설계
- **정확성**: 다양한 YouTube API와 LLM을 조합한 종합적 분석

