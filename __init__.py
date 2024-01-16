"""
A configurable three-dimensional model renderer without OpenGL.

This uses raw math to project and texture your own models.
"""

import pygame
from math import asin, atan2, degrees, tan
from .loader import load


def safe_tri(lst):
    return len(lst) == len(set(lst))


def bary_to_cart(bary, triangle):
    return (
        bary[0] * triangle[0][0] + bary[1] * triangle[1][0] + bary[2] * triangle[2][0],
        bary[0] * triangle[0][1] + bary[1] * triangle[1][1] + bary[2] * triangle[2][1],
    )


def cart_to_bary(cart: tuple[int, int], triangle: list[tuple, tuple, tuple]):
    # Bartriangle[2][1] = 1 - bartriangle[0][1] - bartriangle[1][1]
    # Bartriangle[1][1] = bary[3] - bartriangle[0][1] + 1
    # Bartriangle[0][1] = bartriangle[2][1] - bar[1] + 1
    y2y3 = triangle[1][1] - triangle[2][1]
    x3x2 = triangle[2][0] - triangle[1][0]
    xx2 = cart[0] - triangle[2][0]
    yy2 = cart[1] - triangle[2][1]
    x0x2 = triangle[0][0] - triangle[2][0]
    denominator = y2y3 * x0x2 + x3x2 * (triangle[0][1] - triangle[2][1])

    if denominator == 0:
        return False

    b1 = (y2y3 * xx2 + x3x2 * yy2) / denominator

    b2 = ((triangle[2][1] - triangle[0][1]) * xx2 + x0x2 * yy2) / denominator

    return (b1, b2, 1 - b1 - b2)


def draw_triangle(
    screen,
    triangle: list[tuple[float, float]],
    zs: list[float, float, float],
    uvs: list[tuple[float, float]],
    buffer: list[list[float]],
    texture: pygame.Surface,
):
    txs, tys = zip(*triangle)
    tx, ty = min(txs), min(tys)
    tw, th = max(txs) - tx, max(tys) - ty

    triangle = [(point[0] - tx, point[1] - ty) for point in triangle]
    tsurf = pygame.Surface((tw, th)).convert_alpha()
    tsurf.fill((0, 0, 0, 0))
    for x in range(tsurf.get_width()):
        for y in range(tsurf.get_height()):
            # Get Pixel Value
            bary = cart_to_bary((x, y), triangle)
            if (bary is False) or (bary[0] < 0 or bary[1] < 0 or bary[2] < 0):
                continue
            z = bary[0] * zs[0] + bary[1] * zs[1] + bary[2] * zs[2]
            if buffer[int(x + tx)][int(y + ty)] > z:
                buffer[int(x + tx)][int(y + ty)] = z
                uv = bary_to_cart(bary, uvs)
                uv = int(uv[0] * (texture.get_width() - 1)), int(
                    uv[1] * (texture.get_height() - 1)
                )
                try:
                    tsurf.set_at((x, y), texture.get_at(uv))
                except IndexError:
                    print("oop")

    screen.blit(tsurf, (tx, ty))


def rotate(vert, xyz) -> list:
    """
    Rotates given vertex on the X, Y, and Z dimensions.
    """
    vert.rotate_x_ip(xyz[0])
    vert.rotate_y_ip(xyz[1])
    vert.rotate_z_ip(xyz[2])


class Model:
    def __init__(self, faces, scale) -> None:
        self.raw_faces = faces

        self.faces = [
            [[axis * scale for axis in vertex[:3]] + vertex[-2:] for vertex in face]
            for face in self.raw_faces
        ]
        self.position = pygame.Vector3([0, 0, 0])
        self.rotation = pygame.Vector3([0, 0, 0])

        self.color = (54, 104, 143)

        self.texture = pygame.Surface((1, 1))
        self.texture.fill((150, 150, 150))

    def copy(self):
        m = Model([], 0)
        m.__dict__ = self.__dict__
        return m


class Camera:
    """
    Projects three-dimensional `Models` onto pygame surfaces.

    Uses [weak perspective](https://en.wikipedia.org/wiki/3D_projection#Weak_perspective_projection) projection on all vertices of a model. These are then wireframed and sorted, and finally textured. Note that this is not a ray-caster.
    To use this, simply call `render()` to draw all the models to the screen.
    """

    fov = 80

    def __init__(self) -> None:
        """
        Initializes a physical and virtual camera instance, and specifies all camera information.

        Args:
            objs: A pointer to a list of `Models` to be drawn.
        """
        self.position = pygame.Vector3([0, 0, 0])  # The physical position of the camera
        self.rotation = pygame.Vector3([0, 0, 0])  # The physical rotation of the camera
        self.forward = pygame.Vector3([0, 0, 1])

    # @profile
    def render(self, objects: list, screen: pygame.Surface) -> None:
        # Transformations
        xf, yf = -((screen.get_width() / 2) / tan(self.fov / 2)), -(
            (screen.get_height() / 2) / tan(self.fov / 2)
        )

        buffer = [[float("inf") for _ in range(screen.get_height())] for _ in range(screen.get_width())]
        self.forward.normalize_ip()
        pitch, yaw = degrees(asin(self.forward.y)), degrees(
            atan2(self.forward.x, self.forward.z)
        )
        faces = []
        for obj in objects:
            for face in obj.faces:
                true_face = []
                zs = []
                uvs = []
                for point in face:
                    # Local transforms
                    # Rotation
                    uvs.append(point[-2:])

                    point = point[:3]
                    true_point = pygame.Vector3(point)
                    rotate(true_point, obj.rotation)
                    # Position
                    true_point: pygame.Vector3 = (
                        true_point + obj.position - self.position
                    )

                    # Camera transforms
                    # rotate(true_point, self.rotation)
                    true_point.rotate_y_ip(yaw)
                    true_point.rotate_x_ip(pitch)
                    zs.append(true_point[2])
                    projected = self.project(true_point, xf, yf)

                    true_face.append(
                        (
                            projected[0] + screen.get_width() / 2,
                            projected[1] + screen.get_height() / 2,
                        )
                    )
                faces.append([true_face, zs, uvs, obj.texture])

        # faces = sorted(faces, key=lambda v: min(v[1]), reverse=True)
        for face, z, uvs, texture in faces:
            if min(z) > 0:
                draw_triangle(screen, face, z, uvs, buffer, texture)
                # pygame.draw.polygon(screen, (0,0,0), face, 2)

    def project(self, point: list[int, int, int], xf, yf) -> tuple:
        # TODO: Do not use try/except to sole ZeroDiv. It is slow. Implement culling
        x_projected: float = (point[0] * xf) // (point[2] + xf)
        y_projected: float = (point[1] * yf) // (point[2] + yf)
        return x_projected, y_projected
