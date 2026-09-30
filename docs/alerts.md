# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms` <= 3000ms
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng phải chờ quá lâu (> 3s) để nhận được câu trả lời từ AI assistant, gây suy giảm trải nghiệm sử dụng.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Mở panel Latency trên dashboard để xác định P95/P99 tăng vọt từ thời điểm nào và TTFT có bị tăng theo không.
  2. **Logs**: Lọc trong `data/logs.jsonl` các bản ghi có `event == "response_sent"` và `latency_ms > 3000`, trích xuất `correlation_id` của các request bị ảnh hưởng.
  3. **Traces**: Tìm trace tương ứng với `correlation_id` trên Langfuse, kiểm tra span waterfall xem độ trễ nằm ở span `retrieval` hay `generation`.
- Mitigation tạm thời: Nếu do `retrieval` chậm (vector DB quá tải/timeout), kiểm tra cache/RAG; nếu do `generation` (prompt mới sinh câu trả lời quá dài hoặc model bị nghẽn), rollback prompt `production` về version ổn định trước đó.
- Owner: `student-2A202602717`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Tỉ lệ lỗi tổng thể <= 2% trong 28 ngày
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` liên tục trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng nhận mã lỗi HTTP 500 hoặc thông báo lỗi hệ thống, không nhận được phản hồi từ trợ lý ảo.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Kiểm tra panel Errors trên dashboard để xác nhận error rate hiện tại và loại lỗi phổ biến (`error_type`).
  2. **Logs**: Tìm các sự kiện `event == "request_failed"` trong `data/logs.jsonl`, kiểm tra `payload.detail`, `error_type` và lấy `correlation_id`.
  3. **Traces**: Mở trace trên Langfuse theo `correlation_id` để kiểm tra span gặp exception (ví dụ `retrieval` bị timeout/Vector store timeout hay exception tại API layer).
- Mitigation tạm thời: Nếu vector store lỗi, kích hoạt fallback cơ chế retrieval hoặc bật chế độ trả lời không dùng RAG; khởi động lại service nếu rò rỉ tài nguyên; cách ly model endpoint gặp sự cố.
- Owner: `student-2A202602717`

## Alert 3

- Tên: `LowQualityScore`
- Severity: `warning`
- Duration: `10m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Điểm chất lượng trung bình >= 0.75
- Điều kiện và thời gian duy trì: `mean(quality_score) < 0.75` trong 10 phút
- Ảnh hưởng tới người dùng: Câu trả lời từ AI suy giảm độ chính xác, không đúng ngữ cảnh hoặc bị cắt ngắn, gây giảm độ hài lòng.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Xem panel Quality trên dashboard để quan sát xu hướng điểm trung bình giảm từ mốc thời gian nào.
  2. **Logs**: Tìm các log có `quality_score < 0.75`, kiểm tra `feature`, `model`, `prompt_version` và `answer_preview`.
  3. **Traces**: Vào trace trên Langfuse, so sánh output của generation với context tài liệu được cung cấp trong span `retrieval` để đánh giá tính liên quan (hallucination hoặc prompt formatting lỗi).
- Mitigation tạm thời: Rollback prompt version đang gán nhãn `production` về version trước đó; kiểm tra lại corpus tài liệu RAG có bị thiếu tài liệu phù hợp không.
- Owner: `student-2A202602717`
