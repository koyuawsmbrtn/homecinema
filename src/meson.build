pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'hometheater')
gnome = import('gnome')

gnome.compile_resources('hometheater',
  'hometheater.gresource.xml',
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
  input: 'hometheater.in',
  output: 'hometheater',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

hometheater_sources = [
  'hometheater/__init__.py',
  'hometheater/window.py',
  'hometheater/imdb.py',
  'hometheater/item.py',
  'hometheater/player.py',
  'hometheater/episodes.py',
  'hometheater/tvmaze.py',
  'hometheater/style.css',
  'hometheater/wikipedia.py',
]

install_data(hometheater_sources,
  install_dir: moduledir
)
