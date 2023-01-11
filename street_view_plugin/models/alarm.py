import winsound

class Alarm:

    def beep(self, qty):
        f = 700
        d = 2000
        for i in range(0 , qty):
           winsound.Beep(f,d)
           