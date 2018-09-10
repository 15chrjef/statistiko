from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
import numpy as np
import operator

bad_chars = '()'
data = []
with open("output") as infile:
    for line in infile:
        for c in bad_chars: 
            line = line.replace(c, "")

        obj = tuple(map(float, line.split(',')))
        data.append(obj)

x, y, q, b = zip(*data)
mult = tuple([0.01629*x for x in q])
print(mult)
z = tuple(map(sum, zip(mult, b)))
z = list(map(float, z))
grid_x, grid_y = np.mgrid[min(x):max(x):100j, min(y):max(y):100j]
grid_z = griddata((x, y), z, (grid_x, grid_y), method='cubic')
fig = plt.figure()
ax = fig.gca(projection='3d')
ax.plot_surface(grid_x, grid_y, grid_z, cmap=plt.cm.Spectral)
plt.show()