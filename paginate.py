from itertools import islice


class Pagination:
    def __init__(self, iterable, page=1, per_page=20, total=None):
        self.iterable = iterable
        self.page = page
        self.per_page = per_page
        self.total = total
        if self.total is None:
            try:
                self.total = len(self.iterable)
            except:
                raise RuntimeError('Could not determine length of iterable and no length argument given')
        self.pages = self.total // self.per_page + 1
        if not self.total % self.per_page:
            self.pages = self.pages - 1
        if self.page < 1 or self.page > self.pages:
            raise RuntimeError('Page argument is of range')

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def items(self):
        return islice(iter(self.iterable),
                      self.per_page * (self.page - 1),
                      self.per_page * self.page)

    @property
    def has_prev(self):
        return self.page > 1

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for n in range(1, self.pages + 1):
            if n <= left_edge or \
               (n > self.page - left_current - 1 and
                n < self.page + right_current) or \
               n > self.pages - right_edge:
                if last + 1 != n:
                    yield None
                yield n
                last = n

    @property
    def next(self, error_out=False):
        return Pagination(self.iterable, page=self.page + 1,
                          per_page=self.per_page, total=self.total)

    @property
    def next_num(self):
        return self.page + 1

    @property
    def prev(self, error_out=False):
        return Pagination(self.iterable, page=self.page - 1,
                          per_page=self.per_page, total=self.total)

    @property
    def prev_num(self):
        return self.page - 1
