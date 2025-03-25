pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'videoh')
gnome = import('gnome')

gnome.compile_resources('videoh',
  'videoh.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'videoh.in',
  output: 'videoh',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

videoh_sources = [
  'videoh/__init__.py',
  'videoh/window.py',
  'videoh/imdb.py',
  'videoh/item.py',
  'videoh/player.py',
  'videoh/episodes.py',
  'videoh/tvmaze.py',
  'videoh/style.css',
]

install_data(videoh_sources,
  install_dir: moduledir
)
