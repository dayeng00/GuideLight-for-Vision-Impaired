import threading
import time

# 定义一个简单的计算函数
def count(n):
    while n > 0:
        n -= 1

# 单线程执行
start_time = time.time()
count(100000000)
single_thread_time = time.time() - start_time
print(f"单线程执行时间: {single_thread_time} 秒")

# 多线程执行
n_threads = 2
threads = []
start_time = time.time()
for _ in range(n_threads):
    t = threading.Thread(target=count, args=(50000000,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

multi_thread_time = time.time() - start_time
print(f"多线程执行时间: {multi_thread_time} 秒")

# 比较单线程和多线程执行时间
if multi_thread_time > single_thread_time:
    print("由于GIL的存在，多线程执行时间比单线程长。")
else:
    print("多线程执行时间比单线程短。")