# Giao diện demo (React + shadcn/ui)

Giao diện của `server.py`. Bản build sẵn nằm ở `dist/` — chạy demo chỉ cần `python server.py` ở thư mục gốc.

| Lệnh (trong `web/`) | Việc |
|---|---|
| `npm install` | cài thư viện (chỉ cần khi sửa giao diện) |
| `npm run dev` | chạy giao diện ở `http://localhost:5173`, gọi `/api` sang `python server.py` (cổng 8000) |
| `npm run build` | build ra `dist/` (nhớ commit `dist/`) |

Cấu trúc `src/`:
- `lib/api.ts` — kiểu dữ liệu (giống log JSON của agent) + hàm gọi API, đọc luồng sự kiện khi chạy agent
- `App.tsx` — trạng thái chung: chạy mới / replay, các tab
- `components/app-sidebar.tsx` — thanh bên cấu hình
- `components/run-views.tsx` — dòng thời gian các vòng, ô tổng kết, xem code test (tô đỏ SUSPECTED_BUG, diff)
- `components/charts.tsx` — biểu đồ (recharts qua component `chart` của shadcn)
- `components/results-view.tsx` — kết quả thực nghiệm từ `results/*.csv`
- `components/code-viewer.tsx` — khối code có tô màu cú pháp
- `components/ui/` — component của shadcn/ui (thêm bằng `npx shadcn@latest add <tên>`)
