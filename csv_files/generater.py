import csv
import string
import random
file_name = 'test.csv'

def random_string_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

with open(file_name, 'w', newline='\n') as csvfile:
    writer = csv.writer(csvfile)
    for i in range(1000):
        n_name  = random_string_generator(size=6)
        n_comment = random_string_generator(size= 20)
        n_regionkey = random.randint(0,i)
        writer.writerow([i,n_name,n_regionkey,n_comment])

