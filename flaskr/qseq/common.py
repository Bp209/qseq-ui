def frange(start, stop, step):
    if step == 0:
        raise ValueError('frange() step argument must not be zero')
    if start < stop and step < 0:
        return
    if start > stop and step > 0:
        return
    cur = start
    if start < stop:
        while cur < stop:
            yield cur
            cur += step
    else:
        while cur > stop:
            yield cur
            cur += step
