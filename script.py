from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
import numpy as np
import operator

bad_chars = '()'
data = []
candidate_list = []
current_price = float(input('What is the last price in the data set?: '))

with open("output") as infile:
    for line in infile:
        for c in bad_chars: 
            line = line.replace(c, "")

        obj = tuple(map(float, line.split(',')))
        data.append(obj)

        (x,y,q,b) = tuple(map(float, line.split(',')))
        candidate = (x,y,q*current_price+b)
        candidate_list.append(candidate)


candidate_list.sort(key=lambda x: x[2])
top_ten = list(reversed(candidate_list[-10:]))

print("Top ten:")
for element in top_ten:
	print(element)

x, y, q, b = zip(*data)

mult = tuple([current_price*x for x in q])
#print(mult)
z = tuple(map(sum, zip(mult, b)))
z = list(map(float, z))
grid_x, grid_y = np.mgrid[min(x):max(x):100j, min(y):max(y):100j]
grid_z = griddata((x, y), z, (grid_x, grid_y), method='cubic')
fig = plt.figure()
ax = fig.gca(projection='3d')
ax.plot_surface(grid_x, grid_y, grid_z, cmap=plt.cm.Spectral)
plt.show()