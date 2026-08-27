project(
  'todo',
  version: '1.0.0',
  meson_version: '>= 0.62.0',
  default_options: ['warning_level=2', 'prefix=/usr'],
)

python = import('python')
py_installation = python.find_installation('python3')

prefix = get_option('prefix')
bindir = join_paths(prefix, get_option('bindir'))
datadir = join_paths(prefix, get_option('datadir'))
pkgdatadir = join_paths(datadir, meson.project_name())
localedir = join_paths(prefix, get_option('localedir'))
schemadir = join_paths(datadir, 'glib-2.0', 'schemas')
applicationsdir = join_paths(datadir, 'applications')
metainfodir = join_paths(datadir, 'metainfo')
icondir = join_paths(datadir, 'icons', 'hicolor')

conf = configuration_data()
conf.set('PYTHON', py_installation.full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', localedir)
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'todo.in',
  output: 'todo',
  configuration: conf,
  install: true,
  install_dir: bindir,
  install_mode: 'rwxr-xr-x',
)

install_subdir(
  'src/todo',
  install_dir: py_installation.get_install_dir(),
  exclude_directories: ['__pycache__'],
)

install_data(
  'data/io.github.thanushiyan.Todo.desktop',
  install_dir: applicationsdir,
)

install_data(
  'data/io.github.thanushiyan.Todo.metainfo.xml',
  install_dir: metainfodir,
)

install_data(
  'data/io.github.thanushiyan.Todo.gschema.xml',
  install_dir: schemadir,
)

foreach size : ['16', '24', '32', '48', '64', '128', '256']
  install_data(
    'data/icons/hicolor/@0@x@0@/apps/io.github.thanushiyan.Todo.png'.format(size),
    install_dir: join_paths(icondir, '@0@x@0@'.format(size), 'apps'),
  )
endforeach

install_data(
  'data/icons/hicolor/scalable/apps/io.github.thanushiyan.Todo.svg',
  install_dir: join_paths(icondir, 'scalable', 'apps'),
)

install_data(
  'data/icons/hicolor/symbolic/apps/io.github.thanushiyan.Todo-symbolic.svg',
  install_dir: join_paths(icondir, 'symbolic', 'apps'),
)

gnome = import('gnome')
gnome.post_install(
  glib_compile_schemas: true,
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
