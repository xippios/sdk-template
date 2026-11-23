- From this release on, a release of the template that adds a question to `copier.yml`, or
  a choice to one, ends its section with `### Answers each source passes`: an item per
  source whose update passes an answer that the README's update command does not, holding
  that update's command whole, with every `-d` argument it passes. An adoption copies its
  command from that list, never from the prose of an entry, and a source that the list
  leaves out runs the README's update command as it stands.
  (https://github.com/xippios/sdk-template/issues/245)
