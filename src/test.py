from multiprocessing import Process, Value, Array

def f(n, a):
    n.value = 3.1415927
    for i in range(len(a)):
        a[i] = -a[i]

def mod(a):
    a[5]=42

if __name__ == '__main__':
    num = Value('d', 0.0)
    arr = Array('i', range(10))
    ppot = Process(target=mod, args=(arr,))
    p = Process(target=f, args=(num, arr))
    ppot.start()
    ppot.join()
    p.start()
    p.join()

    print(num.value)
    print(arr[:])