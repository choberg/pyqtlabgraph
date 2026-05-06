# PyQtLabGraph

Ein leistungsstarkes und interaktives Live-Plotting-Widget für PySide6/Qt6, basierend auf PyQtGraph.

`PyQtLabGraph` wurde entwickelt, um wissenschaftliche Daten in Echtzeit zu visualisieren, mit einem besonderen Fokus auf Benutzerfreundlichkeit, Performance und intelligente Achsenskalierung.

## Features

- **Echtzeit-Plotting**: Optimiert für Live-Datenströme (z.B. Sensordaten).
- **Intelligente Achsen (`SmartAxisItem`)**:
  - **Auto**: Klassische SI-Präfixe (k, M, m).
  - **Linear**: Direkte Darstellung von Rohwerten (ideal für Wellenzahlen oder Temperaturen).
  - **Time**: Automatische Formatierung von Sekunden in `d h min s` mit adaptiver Präzision beim Zoomen.
- **Interaktive Legende**: Kurven per Klick ein-/ausblenden oder per Doppelklick direkt stylen.
- **Integrierte Toolbar**:
  - Zoom & Pan (Rechteck-Zoom, X-Zoom, Y-Zoom).
  - Rolling Window (Gleitendes Zeitfenster: Aktuell, 5 min, 30 min, Custom).
  - Home-Button & Export-Funktion (Save as PNG).
- **Vollständig anpassbar**: Customize-Dialog für Farben, Linienstile, Marker (gefüllt/offen) und Achseneinstellungen.
- **Dark Mode Support**: Nahtlose Integration von dunklen und hellen Themes.

## Installation

Direkt aus diesem Repository:

```bash
pip install .
```

Für die lokale Entwicklung können die Abhängigkeiten auch direkt installiert werden:

```bash
pip install PySide6 pyqtgraph
```

## Schnelleinstieg (Demo)

Um die Funktionen auszuprobieren, starten Sie die mitgelieferte Demo aus dem Repository-Root:

```bash
python demo.py
```

Die Demo lädt `maingui.ui` und verwendet die Container `matplotlibContainer`, `toolbarContainer` und `legendContainer` als Einhängepunkte für Plot, Toolbar und Legende.

## Verwendung als Bibliothek

```python
from pyqt_lab_graph import PyQtLabGraphWidget

# Initialisierung (z.B. in einem QMainWindow)
self.plot = PyQtLabGraphWidget(
    plot_container=self.ui.matplotlibContainer,
    toolbar_container=self.ui.toolbarContainer,
    legend_container=self.ui.legendContainer
)

# Achsen konfigurieren
self.plot.set_axis_labels("Zeit", "Spannung", "s", "V", x_mode="time")

# Kurve hinzufügen
self.plot.add_curve("sensor_1", label="Temperatur Sensor")

# Daten hinzufügen
self.plot.add_point("sensor_1", x_value, y_value)
```

## Entwicklung

Schneller Syntax-Check:

```bash
python3 -m py_compile pyqt_lab_graph/*.py demo.py
```

Lokale Paketinstallation im bearbeitbaren Modus:

```bash
pip install -e .
```

## Projektstruktur

- `pyqt_lab_graph/`: Installierbares Python-Package.
- `pyqt_lab_graph/widget.py`: Hauptwidget und öffentliche Plot-API.
- `pyqt_lab_graph/dialogs.py`: Konfigurationsdialoge für Achsen, Raster und Kurvenstile.
- `pyqt_lab_graph/toolbar.py`: Toolbar, Navigation, Export und Rolling-Window-Steuerung.
- `pyqt_lab_graph/legend.py`: Externe Qt-Legende mit Kurven-Sichtbarkeit und Stilzugriff.
- `pyqt_lab_graph/axis.py`: `SmartAxisItem` und Achsenmodi.
- `pyqt_lab_graph/models.py`: Interne Datenmodelle.
- `pyqt_lab_graph/styles.py`: Default-Kurvenfarben und Curve-Style-Helfer.
- `pyqt_lab_graph/theme.py`: Helle/dunkle Theme-Farben und Stylesheets.
- `pyqt_lab_graph/assets/`: Toolbar-Icons, die mit dem Package ausgeliefert werden.
- `demo.py`: Demo-Anwendung mit simulierten Thermostatdaten.
- `maingui.ui`: Qt-Designer-Datei für die Demo.
## Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Sie erlaubt Nutzung, Veränderung und Weiterverbreitung, solange der Copyright- und Lizenzhinweis erhalten bleibt.
