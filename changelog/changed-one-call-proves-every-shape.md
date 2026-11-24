- The template's own CI proves every shape by one call, `scripts/prove.sh --all`, which
  holds the list of the shapes, runs each proof in a process of its own, goes on after one
  that failed and fails where one fails, so a shape added or removed changes the script,
  never the workflow. Its steps and the script no longer liken a shape to a source of the
  family. (https://github.com/xippios/sdk-template/issues/302,
  https://github.com/xippios/sdk-template/issues/304)
