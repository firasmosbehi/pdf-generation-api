# Sample Input Files

These files are designed for realistic manual testing of `POST /generate` using multipart uploads.

## 1) Rich Raw HTML + CSS

Use the operations review sample when you want to upload a complete HTML document and a separate stylesheet.

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "html_file=@./samples/html/operations_review_q4_2025.html;type=text/html" \
  -F "css_file=@./samples/css/operations_review_q4_2025.css;type=text/css" \
  -F "filename=operations-review-q4-2025" \
  --output ./output/operations-review-q4-2025.pdf
```

## 2) Uploaded Jinja Template + Complex JSON Data

Use this path to test template rendering with nested data, conditionals, and repeated sections.

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "template_file=@./samples/template/enterprise_invoice.html;type=text/html" \
  -F "data_file=@./samples/data/enterprise_invoice.json;type=application/json" \
  -F "css_file=@./samples/css/enterprise_invoice.css;type=text/css" \
  -F "filename=enterprise-invoice-2025-11" \
  --output ./output/enterprise-invoice-2025-11.pdf
```

## 3) High-Volume Invoice Variation

This variation includes more line items and milestone rows to stress table rendering and pagination.

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "template_file=@./samples/template/enterprise_invoice.html;type=text/html" \
  -F "data_file=@./samples/data/enterprise_invoice_high_volume.json;type=application/json" \
  -F "css_file=@./samples/css/enterprise_invoice.css;type=text/css" \
  -F "filename=enterprise-invoice-high-volume" \
  --output ./output/enterprise-invoice-high-volume.pdf
```
