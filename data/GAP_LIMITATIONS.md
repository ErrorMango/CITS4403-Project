# Why a Gap Changes the Result

Think of the map as a network of burnable cells. Fire can move from one cell to a neighboring cell, and the algorithm asks a simple question: **Is there any route from the ignition point to the protected area?**

A continuous firebreak cuts every such route. Any path crossing the map has to pass through the firebreak, but those cells are unavailable. In graph terms, the firebreak separates the ignition point from the protected area, so the answer is **no**.

Now open a gap all the way through the firebreak. The cells on either side become connected again, and a route to the protected area exists. The answer changes to **yes**. In our three-cell-wide example, opening one or two cells still leaves the route blocked; opening all three restores it. This is the key result: the gap changes the network's connectivity, even if the total treated area stays the same.

This proves a change in *whether spread is possible in the algorithm*, not how likely or severe a real fire would be. Those outcomes need a fire-spread model and real-world data.
