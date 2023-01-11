
from street_view_plugin.widgets.streetViewDock import StreetViewDock

class WidgetFactory:

    def create(self, widgetName, *args):
        widgets = {
            'StreetViewDock': lambda *args: StreetViewDock(*args)
        }
        return widgets[widgetName](*args) if widgetName in widgets else None