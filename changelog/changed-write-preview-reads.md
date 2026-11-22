- A new source's write scaffold declares its preview, `WritePreview` in `tasks_write.py`,
  tagged `performed: Literal[False]` with `reads`, the operations the preview read, as
  sdk-core ADR-0050 records it, and `/add-endpoint` asks each write task's docstring to say
  whether its preview reads and at what cost. The write server's test that `/add-endpoint`
  gives a source's first write task passes `preview_reads=True`. The scaffold matters to new
  repositories only, since `tasks_write.py` is the source's once rendered.
  (§8, https://github.com/xippios/sdk-template/issues/271)
