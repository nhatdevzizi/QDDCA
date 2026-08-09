import uuid

count = 0


def get_qubit_name():
    """Generate a unique qubit name using a global counter for sequential identifiers."""
    global count
    count += 1
    return "e" + str(count)


class Qubit(object):
    """A quantum information unit transmitted through a quantum network."""

    def __init__(self, name=None, src=None, dest=None, max_try_count=None, birthday=None):
        """Initialize the qubit's basic attributes and transmission parameters."""
        if name is None:
            self.name = get_qubit_name()  # Generate a unique name automatically
        else:
            self.name = name

        self.birth = birthday  # Creation timestamp

        # Transmission endpoints
        self.src = src  # Source node
        self.dest = dest  # Destination node

        # Current state
        self.curr = src  # Current node
        self.route = [self.src]  # Traversed route

        # Transmission control
        self.try_count = 0  # Current attempt count
        self.max_try_count = max_try_count  # Maximum allowed attempts

    def send(self, n):
        """Send the qubit to a new node, update its location, and reset its attempt count."""
        self.try_count = 0  # Reset the attempt count
        self.route.append(n)  # Record the route
        self.curr = n  # Update the current location

        # Check whether the destination has been reached
        if n == self.dest:
            return True
        return False

    def attempt(self):
        """Attempt transmission and check whether the maximum attempt count is exceeded."""
        self.try_count += 1

        # Check whether the maximum attempt count has been exceeded
        if self.try_count > self.max_try_count:
            return False
        return True

    def __repr__(self) -> str:
        """Return the qubit name as its string representation."""
        return self.name
