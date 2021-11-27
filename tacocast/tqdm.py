from tqdm.auto import tqdm as tqdm_aux

def tqdm(iterator, postfix_func=lambda i: {'current': i}, *args, **kwargs):
    with tqdm_aux(iterator, *args, **kwargs) as tq:
        for i in tq:
            tq.set_postfix(postfix_func(i))
            yield i