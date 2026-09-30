# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Trần Tuấn Cường
- **MSSV:** 2A202602717
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/CuongTT-04/K4-L3-DAY13-TranTuanCuong-2A202602717-Monitoring-LLMOps
- **Commit SHA cuối:**
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602717`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Đạt chuẩn schema, correlation ID, enrichment context và PII scrubbing |
| `validate_dashboard.py` | 6/6 panel | 6/6 panel | Hợp lệ 6/6 panel theo đúng contract schema_version 1 |
| `pytest` | 22 passed | 25 passed | Toàn bộ 25 test cases passed (bổ sung test CCCD, credit card, headers) |
| Số traces hợp lệ | 10 | >= 10 | Traces hiển thị đầy đủ root observation, retrieval span và generation |
| Số PII leak | 0 | 0 | Toàn bộ PII (email, sđt, CCCD, thẻ) được che bằng [REDACTED_*] |
| Latency P95 / TTFT P95 | ~1785ms / 50ms | ~1400ms / 50ms | P95 nằm an toàn dưới ngưỡng SLO 3000ms, TTFT ổn định ở 50ms |
| Retrieval success rate | 100% | 100% | 100% các request truy xuất context thành công |


## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware`, middleware nhận header `x-request-id` từ client nếu có, hoặc tự động sinh mã mới theo format `req-<8-hex>` (`req-` kèm 8 ký tự hex ngẫu nhiên từ `uuid.uuid4().hex[:8]`). Sau đó gọi `clear_contextvars()` để tránh rò rỉ context giữa các request, bind `correlation_id` vào structlog contextvars, gắn vào `request.state.correlation_id`, và trả lại mã này cùng `x-response-time-ms` trong response headers.
- **Các metadata được ghi vào structured log:** Các trường cơ sở gồm `ts` (ISO UTC timestamp), `level`, `service`, `event`, `correlation_id`. Tại endpoint `/chat`, log được làm giàu thêm bằng `bind_contextvars`: `user_id_hash` (băm sha256 12 ký tự), `session_id`, `feature`, `model`, và `env`. Khi hoàn thành request, log `response_sent` bổ sung các trường: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`, và `payload` preview.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor `scrub_event` được đăng ký trong cấu hình structlog trước khi render JSON và ghi file. Hàm `scrub_text` sử dụng regex patterns để che toàn bộ email, số điện thoại Việt Nam, CCCD (12 số) và thẻ tín dụng thành `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CCCD]`, `[REDACTED_CREDIT_CARD]`. Ngoài ra, hàm `summarize_text` cũng chủ động scrub PII trên chuỗi message/answer preview.
- **Cách kiểm chứng kết quả:** Chạy `python scripts/validate_logs.py` đạt điểm 100/100 (0 missing required fields, 0 missing enrichment, 10 unique correlation IDs, 0 PII leaks). Toàn bộ 25 test cases trong `pytest` đều pass bao gồm unit test cho PII scrubbing và integration test cho middleware headers.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Project Langfuse `day13-k4-l3b-2A202602717` được cấu hình bằng API keys riêng trong `.env`. Các traces mang `trace_name="day13-agent-request"`, `user_id` là mã băm của `student-2A202602717`, tags `["lab", feature, "claude-sonnet-4-5"]`, và `correlation_id` trong metadata khớp 1-1 với từng dòng trong `data/logs.jsonl`.
- **Cấu trúc root/retrieval/generation observations:**
  - Root observation: `lab-agent-run` (type `agent`) quản lý toàn bộ vòng đời thực thi của agent.
  - Child observation 1: `retrieval` (type `span`) đo thời gian tìm kiếm tài liệu từ corpus và phát hiện vector store timeout/rag_slow.
  - Child observation 2: `generation` (type `generation`) ghi nhận cuộc gọi LLM, lưu trữ metadata `model="claude-sonnet-4-5"`, `usage_details` (tokens in/out/total), `cost_details`, và liên kết trực tiếp tới prompt template qua `propagate_attributes(prompt=...)`.
- **Cách nối trace với log:** Sử dụng trường `correlation_id` chung (định dạng `req-<8-hex>`). Khi điều tra log trong `data/logs.jsonl`, trích xuất `correlation_id` và tìm kiếm trên giao diện Langfuse để mở chính xác waterfall trace tương ứng.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 (gắn nhãn `baseline` và ban đầu là `production`). Template gồm 3 biến: `Feature={{feature}}`, `Docs={{docs}}`, `Question={{message}}`.
- **Version/label candidate:** Version 2 (gắn nhãn `candidate`). Template giữ 3 biến và bổ sung yêu cầu: `Trả lời ngắn gọn và súc tích.`.
- **Trace ID của mỗi version:**
  - Version 1: Tìm trace có `metadata.prompt_version == "1"` trên Langfuse.
  - Version 2: Tìm trace có `metadata.prompt_version == "2"` trên Langfuse.
- **Cách promote và rollback `production`:**
  - Promote: Trên Langfuse UI, dời nhãn `production` từ v1 sang v2. Ứng dụng tự động chuyển sang dùng prompt v2 cho môi trường production mà không cần sửa mã nguồn.
  - Rollback: Khi version mới có dấu hiệu suy giảm chất lượng hoặc tăng chi phí bất thường, trên Langfuse UI dời nhãn `production` quay trở lại v1. Ứng dụng sẽ tự động tải lại v1 sau khi hết chu kỳ cache hoặc sau khi restart API.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dựng theo đặc tả `config/dashboard.yaml` với 6 panel trực quan:
  1. `latency`: Phân vị P50, P95, P99 và TTFT P95 (ms), đường threshold P95 <= 3000ms.
  2. `traffic`: Tổng số request nhận vào và tốc độ theo thời gian (req/phút), threshold >= 1 req/min.
  3. `errors`: Tỉ lệ lỗi tổng thể (%) và tỉ lệ retrieval thành công (%), threshold Error rate <= 2%.
  4. `cost`: Chi phí ước tính theo USD từ token usage, threshold total <= $2.50.
  5. `tokens`: Số lượng token đầu vào (tokens_in) và đầu ra (tokens_out), threshold <= 50,000 tokens.
  6. `quality`: Điểm chất lượng trung bình theo heuristic proxy (0 đến 1), threshold mean >= 0.75.
- **SLO và lý do chọn:** Primary SLO là `fast_successful_requests` với mục tiêu 99.5% trong chu kỳ 28 ngày. Good event: Request xử lý thành công (`event == "response_sent"`) và có độ trễ `latency_ms <= 3000ms` trên tổng số request nhận vào (`event == "request_received"`). Lý do chọn: Ứng dụng AI đối thoại yêu cầu phản hồi nhanh dưới 3s, việc bị lỗi hoặc phản hồi chậm làm đứt gãy luồng tương tác người dùng.
- **Cách tính error budget:** Với mục tiêu SLO 99.5%, error budget là 0.5% trong 28 ngày. Nếu hệ thống phục vụ 10,000 requests trong chu kỳ, số request tối đa được phép không đạt chuẩn (bị lỗi hoặc chậm hơn 3000ms) là `10,000 * 0.5% = 50 requests`.
- **Ba alert và runbook tương ứng:**
  1. `HighLatencyP95` (Warning, P95 latency > 3000ms trong 5m, owner `student-2A202602717`, kênh Slack `#k4-l3b-alerts`, runbook `docs/alerts.md#alert-1`).
  2. `HighErrorRate` (Critical, error rate > 2% trong 5m, owner `student-2A202602717`, kênh Slack `#k4-l3b-alerts`, runbook `docs/alerts.md#alert-2`).
  3. `LowQualityScore` (Warning, mean quality < 0.75 trong 10m, owner `student-2A202602717`, kênh Slack `#k4-l3b-alerts`, runbook `docs/alerts.md#alert-3`).

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** 2026-09-30 04:42:13 UTC – 2026-09-30 04:42:27 UTC (11:42:13 – 11:42:27 theo giờ địa phương).
- **Triệu chứng từ metrics:** Panel `latency` trên dashboard cho thấy độ trễ tăng đột biến: Latency P95 và P99 vọt lên **2652ms** (so với baseline chỉ ~155ms, tăng gấp hơn 17 lần và vượt ngưỡng an toàn `latency_threshold_ms: 2000` của challenge). Trong khi đó, `ttft_ms` vẫn giữ nguyên ở mức 50ms, cho thấy mô hình sinh ngôn ngữ không bị chậm mà thời gian nghẽn xảy ra trước giai đoạn generation.
- **Log line và correlation ID liên quan:**
  - `correlation_id`: `req-df3f07e7` (cùng các request trong batch challenge: `req-d6e4e313`, `req-957581b4`, `req-efdad1e2`, `req-fc98c473`).
  - Log line đại diện:
    ```json
    {"service": "api", "latency_ms": 2652, "ttft_ms": 50, "tokens_in": 35, "tokens_out": 103, "cost_usd": 0.00165, "quality_score": 0.8, "tool_name": "retrieval", "tool_success": true, "payload": {"answer_preview": "Starter answer. You should improve this output logic and add better quality chec..."}, "event": "response_sent", "feature": "monitoring", "session_id": "k4-l3b-challenge-s01", "correlation_id": "req-df3f07e7", "user_id_hash": "4a1a454d70a9", "env": "dev", "model": "claude-sonnet-4-5", "level": "info", "ts": "2026-09-30T04:42:18.680866Z"}
    ```
- **Trace ID và span gây ảnh hưởng:** Mở trace của `correlation_id=req-df3f07e7` trên Langfuse, quan sát cây quan sát waterfall cho thấy:
  - Span `retrieval` tốn **2500ms** (2.5s) chiếm hơn 94% tổng thời gian request.
  - Span `generation` chỉ tốn ~150ms.
  - Kết luận: Span `retrieval` chính là span gây nghẽn nghiêm trọng (bottleneck).
- **Root cause:** Sự cố `rag_slow`: Tầng truy xuất kiến thức / Vector database gặp độ trễ cao bất thường trong quá trình tìm kiếm ngữ cảnh tài liệu cho các câu hỏi thuộc chủ đề `monitoring`.
- **Fix action:** 
  - Khôi phục khẩn cấp: Tắt kịch bản sự cố qua lệnh `python scripts/inject_incident.py --disable`.
  - Khắc phục hệ thống: Kiểm tra tải và tài nguyên trên vector store/cluster RAG; kích hoạt tầng bộ nhớ đệm (cache) cho các truy vấn retrieval thường gặp; cấu hình fallback tạm thời sang tìm kiếm từ khóa (lexical search) nếu vector search quá 1000ms.
- **Preventive measure:**
  - Cấu hình cảnh báo `HighLatencyP95` (P95 > 2000ms kéo dài 5 phút) gửi ngay thông báo tới Slack `#k4-l3b-alerts`.
  - Bổ sung cơ chế timeout chặt chẽ (ví dụ 1000ms) kèm circuit breaker cho hàm `retrieve()`; khi vector store bị chậm quá ngưỡng, tự động trả fallback context hoặc bỏ qua retrieval để bảo vệ SLO độ trễ dưới 3s cho người dùng.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Quyết định sử dụng decorator `@observe` của Langfuse Python SDK v4 cho cả hàm `retrieve` và `FakeLLM.generate` kết hợp `propagate_attributes(prompt=...)`. Quyết định này giúp dựng cây quan sát 3 tầng trực quan (`root agent` -> `retrieval span` -> `generation observation`), tự động kế thừa context/prompt version mà không làm rối code nghiệp vụ.
- **Một lỗi/blocker đã gặp:** Trong quá trình cài đặt ban đầu, máy sử dụng Python 3.14 gây lỗi khi tải và build pre-built wheels cho `pydantic-core`. Ngoài ra, ban đầu trên giao diện Langfuse không thấy tab có tên "Metadata" riêng biệt.
- **Cách tìm nguyên nhân và xử lý:** Chuyển sang tạo venv bằng Python 3.12 (`py -3.12 -m venv .venv`) đã có sẵn wheels tương thích hoàn toàn. Đối với Langfuse, xác định được Metadata nằm trực tiếp trong tab `Attributes` của mỗi span hoặc cuộn xem chi tiết tại panel bên phải.
- **Cách hiểu luồng Metrics → Logs → Traces:** 
  - **Metrics** đóng vai trò cảnh báo sớm (symptom detection), cho biết hệ thống đang suy giảm chỉ số nào (ví dụ P95 latency tăng từ 155ms lên 2652ms) và vào mốc thời gian nào.
  - **Logs** cung cấp ngữ cảnh chi tiết (request context), giúp lọc ra chính xác request cụ thể bị ảnh hưởng thông qua `correlation_id` (`req-df3f07e7`) và ghi nhận dữ liệu không chứa PII.
  - **Traces** mổ xẻ chi tiết nội tại của request đó dưới dạng waterfall spans, cho thấy span `retrieval` tốn 2.5s còn `generation` chỉ tốn 0.15s, từ đó cô lập chính xác nguyên nhân gốc (root cause) mà không cần phỏng đoán.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - Prompt trong LLM tương đương với code trong phần mềm truyền thống: thay đổi prompt có thể dẫn tới hallucination, tăng vọt độ trễ hoặc token cost.
  - Việc quản lý prompt versioning với các labels `baseline`, `candidate`, `production` cho phép promote và rollback tức thì trên Langfuse Cloud mà không phải redeploy ứng dụng.
  - Theo dõi token/cost và thiết lập SLO/error budget giúp đội ngũ vận hành cân bằng giữa chất lượng câu trả lời, trải nghiệm tốc độ của người dùng và chi phí tài nguyên API.
- **Điều quan trọng nhất đã học:** Kỹ năng phân tích sự cố theo chuỗi bằng chứng khách quan (Metrics -> Logs -> Traces) và cách bảo vệ dữ liệu nhạy cảm (PII scrubbing) trong các hệ thống GenAI sản xuất.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Các kịch bản phục hồi khi RAG bị chậm hiện đang dừng ở mức mô phỏng (tắt incident thủ công) chứ chưa có module tự động chuyển mạch (auto circuit breaker/fallback) trong mã nguồn.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
