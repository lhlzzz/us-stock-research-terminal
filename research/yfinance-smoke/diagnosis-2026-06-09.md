# yfinance smoke diagnosis

- yfinance_version: 1.4.1
- cache_dir: /root/.cache/py-yfinance
- proxy_7897: open
- endpoint_query1: {'name': 'query1', 'status': 403, 'content_type': 'text/html', 'len': 3369, 'snippet': '<!DOCTYPE html> <html lang="zh"> <head>     <meta charset="utf-8">     <title>Yahoo</title>     <meta name="viewport" content="width=device-width,initial-scale='}
- endpoint_query2: {'name': 'query2', 'status': 403, 'content_type': 'text/html', 'len': 3369, 'snippet': '<!DOCTYPE html> <html lang="zh"> <head>     <meta charset="utf-8">     <title>Yahoo</title>     <meta name="viewport" content="width=device-width,initial-scale='}
- aapl_5d: {'error': 'YFRateLimitError', 'message': 'Too Many Requests. Rate limited. Try after a while.'}
- rows_6mo:
  - AAPL: {'rows': 0, 'error': 'YFRateLimitError', 'message': 'Too Many Requests. Rate limited. Try after a while.'}
  - MSFT: {'rows': 0, 'error': 'YFRateLimitError', 'message': 'Too Many Requests. Rate limited. Try after a while.'}
  - NVDA: {'rows': 0, 'error': 'YFRateLimitError', 'message': 'Too Many Requests. Rate limited. Try after a while.'}
  - META: {'rows': 0, 'error': 'YFRateLimitError', 'message': 'Too Many Requests. Rate limited. Try after a while.'}
  - AMZN: {'rows': 0, 'error': 'YFRateLimitError', 'message': 'Too Many Requests. Rate limited. Try after a while.'}
  - TSLA: {'rows': 0, 'error': 'YFRateLimitError', 'message': 'Too Many Requests. Rate limited. Try after a while.'}
