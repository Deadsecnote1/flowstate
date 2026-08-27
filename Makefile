.PHONY: run run-flatpak install uninstall deb clean test

run:
	PYTHONPATH=src python3 -m flowstate

run-flatpak:
	./run-flatpak.sh

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

install:
	meson setup build --prefix=/usr
	meson compile -C build
	sudo meson install -C build
	sudo glib-compile-schemas /usr/share/glib-2.0/schemas

uninstall:
	sudo ninja -C build uninstall

deb:
	rm -rf debian/flowstate debian/tmp debian/.debhelper
	dpkg-buildpackage -us -uc -b

clean:
	rm -rf build build-flatpak .flatpak-builder
	rm -rf debian/flowstate debian/tmp debian/.debhelper debian/files debian/debhelper-build-stamp
	dh_clean || true
