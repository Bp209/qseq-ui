import time


i = 4711


class Dummy:
    pass


db = Dummy()


def init():
    db.start_time = time.time()
    print("time's begining")


def timestamp():
    print('%.2f' % (time.time() - db.start_time,))


def a():
    print(i-4669)


def b():
    print("I am the function b")


def c():
    print("Another useless function !")


def final():
    db.start_time = 0
    print("Time's end here")
    print(db.start_time)
