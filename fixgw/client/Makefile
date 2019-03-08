UIFILES = mainWindow.py

all: $(UIFILES)

run: all
	./canfix.py

%.py: %.ui
	pyuic5 -o $@ $<

clean:
	rm $(UIFILES) *.pyc
