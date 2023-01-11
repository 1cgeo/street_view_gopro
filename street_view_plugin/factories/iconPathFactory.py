import os

class IconPathFactory:


    def get(self, iconName):
        iconPaths = {
            'saved': os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                '..',
                'icons',
                'saved.png'
            ),
            'not-saved': os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                '..',
                'icons',
                'not-saved.png'
            ),
            'info': os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                '..',
                'icons',
                'info.png'
            ),
            'warning': os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                '..',
                'icons',
                'warning.png'
            ),
            'ok': os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                '..',
                'icons',
                'ok.png'
            )
        } 
        return iconPaths[iconName] if iconName in iconPaths else ''