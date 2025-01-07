#UIFILES = mainWindow.py itemDialog.py
UIFILES = main_ui.py itemDialog_ui.py

all: $(UIFILES)

run: all
	./canfix.py

%_ui.py: %.ui
	pyuic6 -o $@ $<

clean:
	rm $(UIFILES) *.pyc
