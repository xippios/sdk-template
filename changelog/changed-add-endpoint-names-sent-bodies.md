- `/add-endpoint` names core 0.4.0's `sent_bodies(route)` beside `sent_query` and
  `sent_urls`, for a replay test that checks the bodies its requests sent: a JSON body as
  it parses and a form as a mapping of its fields, credentials redacted. `copier update`
  brings the command. (ADR-0035, https://github.com/xippios/sdk-template/issues/166)
