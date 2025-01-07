#UIFILES = mainWindow.py itemDialog.py
UIFILES = main_ui.py itemDialog_ui.py

all: $(UIFILES)

run: all
	./canfix.py

%_ui.py: %.ui
	pyuic5 -o $@ $<

clean:
	rm $(UIFILES) *.pyc
