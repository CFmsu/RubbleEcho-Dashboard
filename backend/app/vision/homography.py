def solve_linear(matrix: list[list[float]], values: list[float]) -> list[float] | None:
    size = len(values)
    rows = [row[:] + [values[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(rows[row][column]))
        if abs(rows[pivot][column]) < 1e-12:
            return None
        rows[column], rows[pivot] = rows[pivot], rows[column]
        scale = rows[column][column]
        for index in range(column, size + 1):
            rows[column][index] /= scale
        for row in range(size):
            if row == column:
                continue
            factor = rows[row][column]
            for index in range(column, size + 1):
                rows[row][index] -= factor * rows[column][index]
    return [rows[index][size] for index in range(size)]


def solve_homography(
    src: list[tuple[float, float]],
    dst: list[tuple[float, float]],
) -> list[list[float]] | None:
    if len(src) != 4 or len(dst) != 4:
        return None
    equations: list[list[float]] = []
    ordinates: list[float] = []
    for (x_value, y_value), (u_value, v_value) in zip(src, dst):
        equations.append([x_value, y_value, 1, 0, 0, 0, -x_value * u_value, -y_value * u_value])
        ordinates.append(u_value)
        equations.append([0, 0, 0, x_value, y_value, 1, -x_value * v_value, -y_value * v_value])
        ordinates.append(v_value)
    solved = solve_linear(equations, ordinates)
    if solved is None:
        return None
    return [
        [solved[0], solved[1], solved[2]],
        [solved[3], solved[4], solved[5]],
        [solved[6], solved[7], 1.0],
    ]


def apply_homography(
    homography: list[list[float]], x_value: float, y_value: float
) -> tuple[float, float] | None:
    denominator = (
        homography[2][0] * x_value + homography[2][1] * y_value + homography[2][2]
    )
    if abs(denominator) < 1e-12:
        return None
    mapped_x = (
        homography[0][0] * x_value + homography[0][1] * y_value + homography[0][2]
    ) / denominator
    mapped_y = (
        homography[1][0] * x_value + homography[1][1] * y_value + homography[1][2]
    ) / denominator
    return mapped_x, mapped_y
