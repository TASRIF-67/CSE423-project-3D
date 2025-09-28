from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time

#Window settings
window_width = 1000
window_height = 700
cube_title = b"3D Rubik's Cube Simulator"

#Cube parameters
CUBE_SIZE = 50
STICKER_OFFSET = 0.51  # Slightly outside cube face
ANIMATION_SPEED = 5.0  # degrees per frame
BORDER_WIDTH = 2

#Colors for faces (RGB tuples)
COLORS = {
    'W': (1.0, 1.0, 1.0),    # White - Up
    'Y': (1.0, 1.0, 0.0),    # Yellow - Down
    'R': (1.0, 0.0, 0.0),    # Red - Right
    'O': (1.0, 0.5, 0.0),    # Orange - Left
    'B': (0.0, 0.0, 1.0),    # Blue - Front
    'G': (0.0, 1.0, 0.0),    # Green - Back
    None: (0.1, 0.1, 0.1)    # Black - internal faces
}

# Face normal vectors
FACE_NORMALS = {
    (0, 0, 1): 'W',   # +Z (Up)
    (0, 0, -1): 'Y',  # -Z (Down)
    (0, 1, 0): 'B',   # +Y (Front)
    (0, -1, 0): 'G',  # -Y (Back)
    (1, 0, 0): 'R',   # +X (Right)
    (-1, 0, 0): 'O'   # -X (Left)
}

# Global cube configuration
cube_config = {
    'size': 3,          # Default to 3x3x3
    'half_range': 1,    # For 3x3: -1,0,1. For 2x2: -0.5,0.5
    'positions': None   # Will be set based on size
}

# Difficulty settings
DIFFICULTY_LEVELS = {
    2: {  # 2x2 cube
        'Easy': 10,
        'Medium': 20,
        'Hard': 30
    },
    3: {  # 3x3 cube
        'Easy': 20,
        'Medium': 40,
        'Hard': 60
    },
    4: {  # 4x4 cube
        'Easy': 30,
        'Medium': 60,
        'Hard': 90
    }
}

# Statistics tracking
solve_stats = {
    '2x2_Easy': {'times': [], 'best_time': None},
    '2x2_Medium': {'times': [], 'best_time': None},
    '2x2_Hard': {'times': [], 'best_time': None},
    '3x3_Easy': {'times': [], 'best_time': None},
    '3x3_Medium': {'times': [], 'best_time': None},
    '3x3_Hard': {'times': [], 'best_time': None},
    '4x4_Easy': {'times': [], 'best_time': None},
    '4x4_Medium': {'times': [], 'best_time': None},
    '4x4_Hard': {'times': [], 'best_time': None}
}

# Current difficulty
current_difficulty = 'Easy'  # Default difficulty


#Solution Tracker
solution_tracking = {
    'enabled': False,
    'current_step': 0,
    'move_feedback': {
        'color': 'white',  # 'green', 'red', or 'white'
        'display_time': 0,
        'duration': 2.0    # Show color feedback for 2 seconds
    },
    'wrong_move_correction': None  # Add this line
}

class Cubelet:
    def __init__(self, pos, cube_size):
        self.pos = pos  # Position can be fractional for 2x2
        self.cube_size = cube_size
        self.stickers = {}

        # Initialize stickers based on position and cube size
        self.init_stickers()

    def init_stickers(self):
        """Initialize stickers based on position and cube size"""
        x, y, z = self.pos
        half_range = cube_config['half_range']

        print(half_range)
        # Only assign colors to outer faces
        if z == half_range:
            self.stickers[(0, 0, 1)] = 'W'     # Up face (white)
        if z == -half_range:
            self.stickers[(0, 0, -1)] = 'Y'    # Down face (yellow)
        if y == half_range:
            self.stickers[(0, 1, 0)] = 'B'     # Front face (blue)
        if y == -half_range:
            self.stickers[(0, -1, 0)] = 'G'    # Back face (green)
        if x == half_range:
            self.stickers[(1, 0, 0)] = 'R'     # Right face (red)
        if x == -half_range:
            self.stickers[(-1, 0, 0)] = 'O'    # Left face (orange)

    def rotate_stickers(self, axis, clockwise=True):
        """Rotate sticker orientations when cubelet rotates"""
        new_stickers = {}

        for normal, color in self.stickers.items():
            new_normal = rotate_vector(normal, axis, clockwise)
            new_stickers[new_normal] = color
            print(new_stickers)
        self.stickers = new_stickers

def rotate_vector(vec, axis, clockwise=True):
    """Rotate a vector 90 degrees around axis"""
    x, y, z = vec
    ax, ay, az = axis

    if axis == (0, 0, 1):  # Z-axis rotation
        if clockwise:
            return (-y, x, z)
        else:
            return (y, -x, z)
    elif axis == (0, 0, -1):  # -Z-axis rotation
        if clockwise:
            return (y, -x, z)
        else:
            return (-y, x, z)
    elif axis == (1, 0, 0):  # X-axis rotation
        if clockwise:
            return (x, -z, y)
        else:
            return (x, z, -y)
    elif axis == (-1, 0, 0):  # -X-axis rotation
        if clockwise:
            return (x, z, -y)
        else:
            return (x, -z, y)
    elif axis == (0, 1, 0):  # Y-axis rotation
        if clockwise:
            return (z, y, -x)
        else:
            return (-z, y, x)
    elif axis == (0, -1, 0):  # -Y-axis rotation
        if clockwise:
            return (-z, y, x)
        else:
            return (z, y, -x)

    return vec

def rotate_position(pos, axis, clockwise=True):
    """Rotate position around axis by 90 degrees"""
    return rotate_vector(pos, axis, clockwise)

# Global state
cubelets = []
camera = {'pitch': 20, 'yaw': 45, 'distance': 400}
mouse_state = {'dragging': False, 'last_x': 0, 'last_y': 0}
move_queue = []
current_animation = None
game_state = {
    'move_history': [],
    'timer_start': 0,
    'timer_running': False,
    'move_count': 0,
    'scrambled': False,
    'cube_selected': False,
    'solved_by_moves': False,
    'final_time': 0,
}

# UI state
ui_state = {
    'show_help': False,
    'show_menu': True,
    'last_move': None,
    'animation_speed': ANIMATION_SPEED,
    'menu_selection': 0,      # 0=2x2, 1=3x3
    'difficulty_selection': 0, # 0=Easy, 1=Medium, 2=Hard
    'menu_stage': 'cube_size', # 'cube_size' or 'difficulty'
    'solution_moves': [],
    'show_solution': False,
    'celebration': {
        'active': False,
        'start_time': 0,
        'duration': 5.0,
        'message_alpha': 0.0,
        'cube_spin': 0.0,
        'timer_blink': False,
        'particles': []
    }
}

def setup_cube_size(size):
    """Setup cube configuration based on size"""
    global cube_config

    cube_config['size'] = size

    if size == 2:
        cube_config['half_range'] = 0.5
        cube_config['positions'] = [-0.5, 0.5]
        print("Configured for 2x2x2 cube")
    elif size == 3:
        cube_config['half_range'] = 1
        cube_config['positions'] = [-1, 0, 1]
        print("Configured for 3x3x3 cube")
    elif size == 4:
        cube_config['half_range'] = 1.5
        cube_config['positions'] = [-1.5, -0.5, 0.5, 1.5]
        print("Configured for 4x4x4 cube")


def init_cube():
    """Initialize the cube in solved state based on current size"""
    global cubelets
    cubelets = []

    positions = cube_config['positions']
    size = cube_config['size']

    print(f"Initializing {size}x{size}x{size} cube...")

    for x in positions:
        for y in positions:
            for z in positions:
                cubelets.append(Cubelet((x, y, z), size))

    #Debug: Check cube initialization
    visible_faces = 0
    for cubelet in cubelets:
        visible_faces += len(cubelet.stickers)

    expected_stickers = 6 * size * size  # 6 faces, size*size stickers each

    print(f"Total cubelets: {len(cubelets)}")
    print(f"Total visible stickers: {visible_faces}")
    print(f"Expected: {expected_stickers} stickers")

    # Print face distribution
    face_counts = {'W': 0, 'Y': 0, 'R': 0, 'O': 0, 'B': 0, 'G': 0}
    for cubelet in cubelets:
        for color in cubelet.stickers.values():
            if color in face_counts:
                face_counts[color] += 1

    print("Face distribution:", face_counts)


def get_face_cubelets(face):
    """Get cubelets belonging to a face (works for 2x2, 3x3, and 4x4)"""
    face_cubelets = []
    half_range = cube_config['half_range']

    #store (axis_index, expected_value)
    face_axes = {
        'U': (2, half_range),     # Up face → z = +half_range
        'D': (2, -half_range),    # Down face → z = -half_range
        'R': (0, half_range),     # Right face → x = +half_range
        'L': (0, -half_range),    # Left face → x = -half_range
        'F': (1, half_range),     # Front face → y = +half_range
        'B': (1, -half_range)     # Back face → y = -half_range
    }

    if face in face_axes:
        axis, expected_value = face_axes[face]
        for cubelet in cubelets:
            if cubelet.pos[axis] == expected_value:
                face_cubelets.append(cubelet)

    return face_cubelets

def get_face_axis(face):
    """Get rotation axis for face"""
    axes = {
        'U': (0, 0, 1),   'D': (0, 0, -1),
        'R': (1, 0, 0),   'L': (-1, 0, 0),
        'F': (0, 1, 0),   'B': (0, -1, 0)
    }
    return axes.get(face, (0, 0, 1))

def rotate_face(face, clockwise=True, double=False):
    """Add face rotation to animation queue"""
    global move_queue

    if not game_state['cube_selected']:
        print("Please select cube size first!")
        return

    if double:
        move_queue.append({'face': face, 'clockwise': clockwise, 'angle': 180})
    else:
        move_queue.append({'face': face, 'clockwise': clockwise, 'angle': 90})

    # Update move history
    direction = "" if clockwise else "'"
    if double:
        direction = "2"

    move_notation = face + direction
    game_state['move_history'].append(move_notation)

    # Only increment move count if not scrambling
    if not game_state.get('is_scrambling', False):
        game_state['move_count'] += 1

    ui_state['last_move'] = move_notation

    # For solution tracking feedback
    validate_user_move(move_notation)

    # START TIMER ON FIRST MANUAL MOVE
    if (game_state['scrambled'] and
        not game_state['timer_running'] and
        not ui_state['celebration']['active'] and
        not game_state.get('is_scrambling', False)):


        game_state['timer_start'] = time.time()
        game_state['timer_running'] = True
        print("Timer started!")

    print(f"Move queued: {move_notation}")

def draw_sticker(normal, color, size):
    """Draw a single sticker on cube face with proper normals"""
    if color is None:
        return  # Don't draw internal faces

    glColor3f(*COLORS[color])

    # Set the normal for proper lighting
    glNormal3f(*normal)

    # Calculate sticker vertices based on normal
    x, y, z = normal
    half = size * 0.4  # Sticker is smaller than face
    offset = size * STICKER_OFFSET

    glBegin(GL_QUADS)

    if abs(z) == 1:  # Top/Bottom faces
        # Ensure correct winding order for normals
        if z > 0:  # Top face
            glVertex3f(-half, -half, z * offset)
            glVertex3f(half, -half, z * offset)
            glVertex3f(half, half, z * offset)
            glVertex3f(-half, half, z * offset)
        else:  # Bottom face
            glVertex3f(-half, half, z * offset)
            glVertex3f(half, half, z * offset)
            glVertex3f(half, -half, z * offset)
            glVertex3f(-half, -half, z * offset)
    elif abs(y) == 1:  # Front/Back faces
        if y > 0:  # Front face
            glVertex3f(-half, y * offset, -half)
            glVertex3f(half, y * offset, -half)
            glVertex3f(half, y * offset, half)
            glVertex3f(-half, y * offset, half)
        else:  # Back face
            glVertex3f(half, y * offset, -half)
            glVertex3f(-half, y * offset, -half)
            glVertex3f(-half, y * offset, half)
            glVertex3f(half, y * offset, half)
    elif abs(x) == 1:  # Left/Right faces
        if x > 0:  # Right face
            glVertex3f(x * offset, -half, -half)
            glVertex3f(x * offset, half, -half)
            glVertex3f(x * offset, half, half)
            glVertex3f(x * offset, -half, half)
        else:  # Left face
            glVertex3f(x * offset, half, -half)
            glVertex3f(x * offset, -half, -half)
            glVertex3f(x * offset, -half, half)
            glVertex3f(x * offset, half, half)

    glEnd()

def draw_cubelet(cubelet):
    """Draw a single cubelet with stickers"""
    x, y, z = cubelet.pos

    # Adjust spacing based on cube size
    spacing = CUBE_SIZE * 1.1

    glPushMatrix()
    glTranslatef(x * spacing, y * spacing, z * spacing)

    # Draw core cube (dark) with proper normal
    glColor3f(0.1, 0.1, 0.1)
    glNormal3f(0, 0, 1)  # Default normal
    glutSolidCube(CUBE_SIZE * 0.9)

    # Disable lighting for stickers to get pure colors
    glDisable(GL_LIGHTING)

    # Draw stickers
    for normal, color in cubelet.stickers.items():
        draw_sticker(normal, color, CUBE_SIZE)

    # Re-enable lighting
    glEnable(GL_LIGHTING)

    glPopMatrix()

def draw_cube():
    """Draw entire cube"""
    for cubelet in cubelets:
        draw_cubelet(cubelet)

def draw_animated_cube():
    """Draw cube with current animation"""
    global current_animation

    if current_animation is None:
        draw_cube()
        return

    face = current_animation['face']
    axis = get_face_axis(face)
    angle = current_animation['current_angle']
    clockwise = current_animation['clockwise']

    if not clockwise:
        angle = -angle

    face_cubelets = get_face_cubelets(face)

    # Draw non-rotating cubelets
    for cubelet in cubelets:
        if cubelet not in face_cubelets:
            draw_cubelet(cubelet)

    # Draw rotating cubelets with transformation
    glPushMatrix()
    glRotatef(angle, *axis)

    for cubelet in face_cubelets:
        draw_cubelet(cubelet)

    glPopMatrix()

def setup_camera():
    """Setup 3D camera"""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, window_width / window_height, 0.1, 1000)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # Calculate camera position
    pitch_rad = math.radians(camera['pitch'])
    yaw_rad = math.radians(camera['yaw'])

    cam_x = camera['distance'] * math.cos(pitch_rad) * math.cos(yaw_rad)
    cam_y = camera['distance'] * math.cos(pitch_rad) * math.sin(yaw_rad)
    cam_z = camera['distance'] * math.sin(pitch_rad)

    gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 0, 1)

def setup_lighting():
    """Setup improved lighting to reduce distortion"""
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHT1)

    # Primary light
    light_pos = [200, 200, 200, 1.0]
    light_ambient = [0.4, 0.4, 0.4, 1.0]  # Increased ambient
    light_diffuse = [0.7, 0.7, 0.7, 1.0]  # Reduced diffuse
    light_specular = [0.2, 0.2, 0.2, 1.0]  # Add specular

    glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
    glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
    glLightfv(GL_LIGHT0, GL_SPECULAR, light_specular)

    # Secondary fill light to reduce harsh shadows
    light_pos2 = [-200, -200, 200, 1.0]
    light_ambient2 = [0.2, 0.2, 0.2, 1.0]
    light_diffuse2 = [0.3, 0.3, 0.3, 1.0]

    glLightfv(GL_LIGHT1, GL_POSITION, light_pos2)
    glLightfv(GL_LIGHT1, GL_AMBIENT, light_ambient2)
    glLightfv(GL_LIGHT1, GL_DIFFUSE, light_diffuse2)

    # Set material properties
    glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, [50.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.2, 0.2, 0.2, 1.0])

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    """Draw 2D text overlay"""
    glColor3f(1.0, 1.0, 1.0)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_LIGHTING)
    glRasterPos2f(x, y)
    for char in text:
        glutBitmapCharacter(font, ord(char))
    glEnable(GL_LIGHTING)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_menu():
    """Draw cube size and difficulty selection menu"""
    if not ui_state['show_menu']:
        return

    # Draw semi-transparent overlay
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)
    glColor4f(0.0, 0.0, 0.0, 0.7)

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    # Draw background rectangle
    glBegin(GL_QUADS)
    glVertex2f(0, 0)
    glVertex2f(window_width, 0)
    glVertex2f(window_width, window_height)
    glVertex2f(0, window_height)
    glEnd()

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    glDisable(GL_BLEND)

    center_x = window_width // 2 - 200
    center_y = window_height // 2

    if ui_state['menu_stage'] == 'cube_size':
        draw_cube_size_menu(center_x, center_y)
    else:  # difficulty selection
        draw_difficulty_menu(center_x, center_y)

    glEnable(GL_LIGHTING)

def draw_cube_size_menu(center_x, center_y):
    """Draw cube size selection with 4x4 option"""
    draw_text(center_x, center_y + 150, "3D Rubik's Cube Simulator", GLUT_BITMAP_TIMES_ROMAN_24)
    draw_text(center_x, center_y + 100, "Select Cube Size:", GLUT_BITMAP_HELVETICA_18)

    # Draw options with selection indicator
    options = ["2x2x2 Cube", "3x3x3 Cube", "4x4x4 Cube"]

    for i, option in enumerate(options):
        y_pos = center_y + 50 - i * 30
        if ui_state['menu_selection'] == i:
            draw_text(center_x, y_pos, f"> {option}", GLUT_BITMAP_HELVETICA_18)
        else:
            draw_text(center_x, y_pos, f"  {option}", GLUT_BITMAP_HELVETICA_18)

    draw_text(center_x, center_y - 50, "Use UP/DOWN arrows to select", GLUT_BITMAP_HELVETICA_12)
    draw_text(center_x, center_y - 70, "Press ENTER to continue", GLUT_BITMAP_HELVETICA_12)



def draw_difficulty_menu(center_x, center_y):
    """Draw difficulty selection with 4x4 support"""
    cube_sizes = [2, 3, 4]
    selected_cube_size = cube_sizes[ui_state['menu_selection']]

    draw_text(center_x, center_y + 150, f"Select Difficulty for {selected_cube_size}x{selected_cube_size} Cube:", GLUT_BITMAP_HELVETICA_18)

    difficulties = ['Easy', 'Medium', 'Hard']

    for i, difficulty in enumerate(difficulties):
        y_pos = center_y + 80 - i * 50
        scramble_moves = DIFFICULTY_LEVELS[selected_cube_size][difficulty]

        # Get stats for this mode
        solve_count = get_solve_count(selected_cube_size, difficulty)
        best_time = get_best_time(selected_cube_size, difficulty)

        # Selection indicator
        prefix = "> " if ui_state['difficulty_selection'] == i else "  "

        # Main difficulty info
        main_text = f"{prefix}{difficulty} - {scramble_moves} moves"
        draw_text(center_x, y_pos, main_text, GLUT_BITMAP_HELVETICA_18)

        # Stats
        stats_text = f"    Solves: {solve_count}"
        if best_time:
            stats_text += f" | Best: {best_time:.2f}s"
        else:
            stats_text += " | Best: None"

        draw_text(center_x, y_pos - 20, stats_text, GLUT_BITMAP_HELVETICA_12)

    draw_text(center_x, center_y - 80, "Use UP/DOWN arrows to select", GLUT_BITMAP_HELVETICA_12)
    draw_text(center_x, center_y - 100, "Press ENTER to start", GLUT_BITMAP_HELVETICA_12)
    draw_text(center_x, center_y - 120, "Press BACKSPACE to go back", GLUT_BITMAP_HELVETICA_12)
    draw_text(center_x, center_y - 120, "Press BACKSPACE to go back", GLUT_BITMAP_HELVETICA_12)

def draw_ui():
    """Draw user interface"""
    if ui_state['show_menu']:
        return

    # Current mode display (always at top)
    cube_size = cube_config['size']
    scramble_moves = get_scramble_length()
    mode_text = f"Mode: {cube_size}x{cube_size} {current_difficulty} ({scramble_moves} moves)"
    draw_text(10, window_height - 30, mode_text, GLUT_BITMAP_HELVETICA_18)

    # Current mode stats
    current_best = get_best_time(cube_size, current_difficulty)
    solve_count = get_solve_count(cube_size, current_difficulty)
    if current_best:
        stats_text = f"Best: {current_best:.2f}s | Solves: {solve_count}"
    else:
        stats_text = f"Best: None | Solves: {solve_count}"
    draw_text(10, window_height - 60, stats_text)

    # Timer and moves
    if game_state['timer_running']:
        elapsed = time.time() - game_state['timer_start']
        timer_text = f"Time: {elapsed:.1f}s"
    else:
        timer_text = "Timer: Stopped"

    draw_text(10, window_height - 90, timer_text)
    draw_text(10, window_height - 120, f"Moves: {game_state['move_count']}")

    # Double move indicator
    global double_move_pending
    if double_move_pending:
        glColor3f(1.0, 1.0, 0.0)  # Yellow color for double move indicator
        draw_text(10, window_height - 150, "Double Move Mode - Press face key!")
        glColor3f(1.0, 1.0, 1.0)  # Reset to white
        next_line = 180
    else:
        next_line = 150

    # Last move with color feedback
    if ui_state['last_move']:
        # Set color based on move feedback
        feedback_color = solution_tracking['move_feedback']['color']
        if feedback_color == 'green':
            glColor3f(0.0, 1.0, 0.0)  # Green for correct
        elif feedback_color == 'red':
            glColor3f(1.0, 0.0, 0.0)  # Red for wrong
        else:
            glColor3f(1.0, 1.0, 1.0)  # White for normal

        draw_text(10, window_height - next_line, f"Last: {ui_state['last_move']}")

        # Reset color back to white for other text
        glColor3f(1.0, 1.0, 1.0)

        next_line += 30

    # Move history (last 5 moves)
    if game_state['move_history']:
        recent_moves = game_state['move_history'][-5:]
        history_text = " ".join(recent_moves)
        draw_text(10, window_height - next_line, f"History: {history_text}")
        next_line += 30

    # Solution tracking status
    if solution_tracking['enabled']:
        current_step = solution_tracking['current_step']
        total_steps = len(ui_state['solution_moves'])
        if current_step < total_steps:
            next_move = ui_state['solution_moves'][current_step]
            glColor3f(0.0, 1.0, 1.0)  # Cyan for guidance
            draw_text(10, window_height - next_line, f"Next move: {next_move} ({current_step + 1}/{total_steps})")
            glColor3f(1.0, 1.0, 1.0)  # Reset to white
            next_line += 30

    # Show solution moves if available
    if ui_state['show_solution'] and ui_state['solution_moves']:
        draw_text(10, window_height - next_line, "Solution moves:")
        next_line += 30

        # Display solution in chunks of 8 moves per line with color coding
        solution = ui_state['solution_moves']
        current_step = solution_tracking['current_step'] if solution_tracking['enabled'] else -1

        for i in range(0, len(solution), 8):
            chunk = solution[i:i+8]
            line_text = ""

            # Build the line text first
            for j, move in enumerate(chunk):
                if j > 0:
                    line_text += " "
                line_text += move

            # Now draw each move with appropriate color
            x_start = 10
            current_x = x_start

            # Disable lighting for text rendering
            glDisable(GL_LIGHTING)

            # Set up 2D projection for text
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            gluOrtho2D(0, window_width, 0, window_height)

            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()

            for j, move in enumerate(chunk):
                move_index = i + j

                # Determine color for this move
                if solution_tracking['enabled']:
                    if move_index < current_step:
                        # Completed moves - green
                        glColor3f(0.0, 1.0, 0.0)
                    elif move_index == current_step:
                        # Current move - cyan/yellow highlight
                        glColor3f(1.0, 1.0, 0.0)
                    else:
                        # Future moves - white
                        glColor3f(1.0, 1.0, 1.0)
                else:
                    # No tracking - all white
                    glColor3f(1.0, 1.0, 1.0)

                # Draw the move
                glRasterPos2f(current_x, window_height - next_line)
                for char in move:
                    glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(char))

                # Calculate approximate width and move to next position
                move_width = len(move) * 7  # Approximate character width
                current_x += move_width + 10  # Add spacing between moves

            # Restore matrices
            glPopMatrix()
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)

            # Re-enable lighting
            glEnable(GL_LIGHTING)

            next_line += 25

    # Reset color to white for subsequent text
    glColor3f(1.0, 1.0, 1.0)

    # Controls hint at the bottom of the screen
    draw_text(10, 30, "Press H - Toggle Help | M - Back to Menu | E - Enable/Disable Move Validation")

    # Controls help
    if ui_state['show_help']:
        help_text = [
            "Controls:",
            "U/D/L/R/F/B - Face rotations",
            "Shift + key - Prime moves",
            "2 + key - Double moves",
            "S - Scramble",
            "V - Show solution moves",
            "C - Hide solution",
            "E - Enable/Disable move validation",
            "Space - Reset",
            "T - Toggle timer",
            "H - Toggle help",
            "M - Back to menu",
            "Mouse - Rotate camera"
        ]

        for i, line in enumerate(help_text):
            draw_text(400, window_height - 50 - i * 25, line)

def get_scramble_length():
    """Get appropriate scramble length based on cube size and difficulty"""
    cube_size = cube_config['size']
    return DIFFICULTY_LEVELS[cube_size][current_difficulty]

def show_solution():
    """Display the solution moves with difficulty context"""
    if not game_state['move_history'] or not game_state['scrambled']:
        print("No scramble to solve!")
        return

    # Generate solution moves
    solution_moves = []
    for move in reversed(game_state['move_history']):
        inverse = get_inverse_move(move)
        solution_moves.append(inverse)

    scramble_moves = get_scramble_length()
    print(f"Original scramble ({current_difficulty} - {scramble_moves} moves): {' '.join(game_state['move_history'])}")
    print(f"Solution moves: {' '.join(solution_moves)}")

    # Store solution for UI display
    ui_state['solution_moves'] = solution_moves
    ui_state['show_solution'] = True

def get_inverse_move(move):
    """Get the inverse of a move"""
    if move.endswith("'"):
        return move[0]  # R' becomes R
    elif move.endswith("2"):
        return move      # R2 stays R2 (its own inverse)
    else:
        return move + "'" # R becomes R'

def scramble_cube(moves=None):
    """Generate random scramble based on cube size"""
    if not game_state['cube_selected']:
        print("Please select cube size first!")
        return

    # Set scrambling flag
    game_state['is_scrambling'] = True

    # Reset game state when scrambling
    game_state['solved_by_moves'] = False
    game_state['move_count'] = 0  # Reset move count before scrambling
    ui_state['celebration']['active'] = False
    ui_state['solution_moves'] = []
    ui_state['show_solution'] = False

    if moves is None:
        moves = get_scramble_length()

    faces = ['U', 'D', 'L', 'R', 'F', 'B']
    modifiers = ['', "'", "2"]

    scramble = []  # Initialize scramble list
    last_face = None

    for _ in range(moves):
        # Avoid same face twice in a row
        available_faces = [f for f in faces if f != last_face]
        face = random.choice(available_faces)
        modifier = random.choice(modifiers)

        scramble.append(face + modifier)
        last_face = face

    # Apply scramble
    for move in scramble:
        face = move[0]
        if len(move) > 1:
            if move[1] == "'":
                rotate_face(face, clockwise=False)
            elif move[1] == "2":
                rotate_face(face, clockwise=True, double=True)
        else:
            rotate_face(face, clockwise=True)

    # Clear scrambling flag
    game_state['is_scrambling'] = False

    game_state['scrambled'] = True
    print(f"Scramble ({cube_config['size']}x{cube_config['size']}): {' '.join(scramble)}")
    print("Timer will start when you make your first move!")


#Celebration functions
def is_cube_solved():
    """Check if the cube is in solved state"""
    if not cubelets:
        return False

    # Define expected colors for each face in solved state
    expected_faces = {
        'W': [],  # White (Up)
        'Y': [],  # Yellow (Down)
        'R': [],  # Red (Right)
        'O': [],  # Orange (Left)
        'B': [],  # Blue (Front)
        'G': []   # Green (Back)
    }

    # Collect all stickers by their normals
    for cubelet in cubelets:
        for normal, color in cubelet.stickers.items():
            if normal == (0, 0, 1):   expected_faces['W'].append(color)
            elif normal == (0, 0, -1): expected_faces['Y'].append(color)
            elif normal == (1, 0, 0):  expected_faces['R'].append(color)
            elif normal == (-1, 0, 0): expected_faces['O'].append(color)
            elif normal == (0, 1, 0):  expected_faces['B'].append(color)
            elif normal == (0, -1, 0): expected_faces['G'].append(color)

    # Check if each face has uniform color
    for face_color, stickers in expected_faces.items():
        if not stickers:  # No stickers on this face
            continue
        if not all(color == face_color for color in stickers):
            return False

    return True

def start_celebration():
    """Start the celebration animation"""
    ui_state['celebration']['active'] = True
    ui_state['celebration']['start_time'] = time.time()
    ui_state['celebration']['message_alpha'] = 0.0
    ui_state['celebration']['cube_spin'] = 0.0

    # Stop timer and record final time
    if game_state['timer_running']:
        game_state['timer_running'] = False
        game_state['final_time'] = time.time() - game_state['timer_start']
    else:
        game_state['final_time'] = 0

    # Record solve time and check for new best
    is_new_best = False
    if game_state['final_time'] > 0:
        is_new_best = record_solve_time(game_state['final_time'])

    # Store if it's a new best for celebration display
    ui_state['celebration']['is_new_best'] = is_new_best

    # Clear solution moves when cube is solved
    ui_state['solution_moves'] = []
    ui_state['show_solution'] = False

    print("🎉 CONGRATULATIONS! CUBE SOLVED! 🎉")
    if game_state['final_time'] > 0:
        print(f"Time: {game_state['final_time']:.2f} seconds")
    print(f"Moves: {game_state['move_count']}")
    print(f"Mode: {cube_config['size']}x{cube_config['size']} {current_difficulty}")

def update_celebration():
    """Update celebration animation"""
    if not ui_state['celebration']['active']:
        return

    current_time = time.time()
    elapsed = current_time - ui_state['celebration']['start_time']
    progress = elapsed / ui_state['celebration']['duration']

    if progress >= 1.0:
        # End celebration
        ui_state['celebration']['active'] = False
        return

    # Update message fade-in
    if progress < 0.5:
        ui_state['celebration']['message_alpha'] = progress * 2.0
    else:
        ui_state['celebration']['message_alpha'] = 1.0

    # Update cube spin
    ui_state['celebration']['cube_spin'] += 2.0

    # Timer blink effect (blinks every 0.3 seconds)
    ui_state['celebration']['timer_blink'] = (int(elapsed * 3) % 2) == 0

def draw_celebration_message():
    """Draw congratulations message"""
    alpha = ui_state['celebration']['message_alpha']

    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)

    # Draw background
    glColor4f(0.0, 0.0, 0.5, 0.8 * alpha)

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    # Background rectangle
    glBegin(GL_QUADS)
    glVertex2f(window_width//6, window_height//4)
    glVertex2f(5*window_width//6, window_height//4)
    glVertex2f(5*window_width//6, 3*window_height//4)
    glVertex2f(window_width//6, 3*window_height//4)
    glEnd()

    center_y = window_height // 2

    # Main message
    glColor4f(1.0, 0.8, 0.0, alpha)
    draw_text_centered("CONGRATULATIONS!", center_y + 80)

    glColor4f(0.0, 1.0, 0.0, alpha)
    draw_text_centered("CUBE SOLVED!", center_y + 40)

    # Timer display with blinking
    if game_state['final_time'] > 0:
        if ui_state['celebration']['timer_blink']:
            glColor4f(1.0, 1.0, 0.0, alpha)  # Bright yellow
        else:
            glColor4f(0.8, 0.8, 0.0, alpha * 0.6)  # Dim yellow

        time_text = f"TIME: {game_state['final_time']:.2f} seconds"
        draw_text_centered(time_text, center_y)

    # Move count
    glColor4f(1.0, 1.0, 1.0, alpha)
    moves_text = f"MOVES: {game_state['move_count']}"
    draw_text_centered(moves_text, center_y - 30)

    # Continue message
    glColor4f(0.9, 0.9, 0.9, alpha * 0.8)
    draw_text_centered("Press SPACE to reset", center_y - 80)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    glDisable(GL_BLEND)
    glEnable(GL_LIGHTING)


#Helper functions
def get_current_mode_key():
    """Get the key for current cube size and difficulty"""
    cube_size = cube_config['size']
    return f"{cube_size}x{cube_size}_{current_difficulty}"

def get_scramble_length():
    """Get scramble length based on cube size and difficulty"""
    cube_size = cube_config['size']
    return DIFFICULTY_LEVELS[cube_size][current_difficulty]

def record_solve_time(solve_time):
    """Record solve time and update best time"""
    key = get_current_mode_key()
    solve_stats[key]['times'].append(solve_time)

    if solve_stats[key]['best_time'] is None or solve_time < solve_stats[key]['best_time']:
        solve_stats[key]['best_time'] = solve_time
        print(f"🏆 NEW BEST TIME! {solve_time:.2f}s for {cube_config['size']}x{cube_config['size']} {current_difficulty}")
        return True
    return False

def get_solve_count(cube_size, difficulty):
    """Get total number of solves for a specific mode"""
    key = f"{cube_size}x{cube_size}_{difficulty}"
    return len(solve_stats[key]['times'])

def get_best_time(cube_size, difficulty):
    """Get best time for a specific mode"""
    key = f"{cube_size}x{cube_size}_{difficulty}"
    return solve_stats[key]['best_time']


def draw_text_centered(text, y):
    """Draw centered text"""
    text_width = len(text) * 7
    x = (window_width - text_width) // 2

    glRasterPos2f(x, y)
    for char in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
#Functions to handle solution tracker
def enable_solution_tracking():
    """Enable move validation against solution"""
    if ui_state['solution_moves'] and ui_state['show_solution']:
        solution_tracking['enabled'] = True
        solution_tracking['current_step'] = 0
        solution_tracking['move_feedback']['color'] = 'white'
        solution_tracking['wrong_move_correction'] = None  # Use dictionary access
        print("Move validation enabled! Follow the solution moves.")
        print(f"Next move: {ui_state['solution_moves'][0] if ui_state['solution_moves'] else 'None'}")
    else:
        print("Show solution first (press V) to enable move validation")


def disable_solution_tracking():
    """Disable move validation"""
    solution_tracking['enabled'] = False
    solution_tracking['current_step'] = 0
    solution_tracking['move_feedback']['color'] = 'white'
    print("Move validation disabled")

def validate_user_move(move):
    """Validate user move against expected solution move"""
    if not solution_tracking['enabled'] or not ui_state['solution_moves']:
        return

    current_step = solution_tracking['current_step']

    if current_step >= len(ui_state['solution_moves']):
        # All solution moves completed
        solution_tracking['enabled'] = False
        print("Solution complete!")
        return

    expected_move = ui_state['solution_moves'][current_step]

    # Track wrong moves and their corrections
    if solution_tracking['wrong_move_correction'] is not None:
        # If we're correcting a wrong move
        if solution_tracking['wrong_move_correction']['move'] == move:
            solution_tracking['wrong_move_correction']['count'] += 1

            # Check if we've made enough correction moves
            if solution_tracking['wrong_move_correction']['count'] >= solution_tracking['wrong_move_correction']['needed']:
                # Reset wrong move tracking
                solution_tracking['wrong_move_correction'] = None
                # Now we can proceed with the expected move
                solution_tracking['move_feedback']['color'] = 'white'
                print(f"Position corrected. Now make the expected move: {expected_move}")
            else:
                solution_tracking['move_feedback']['color'] = 'red'
                remaining = solution_tracking['wrong_move_correction']['needed'] - solution_tracking['wrong_move_correction']['count']
                print(f"Keep correcting: need {remaining} more {move} moves")
            return

    # Check if the move matches the expected move
    if move == expected_move:
        # Correct move
        solution_tracking['move_feedback']['color'] = 'green'
        solution_tracking['move_feedback']['display_time'] = time.time()
        solution_tracking['current_step'] += 1
        solution_tracking['wrong_move_correction'] = None  # Reset wrong move tracking

        remaining = len(ui_state['solution_moves']) - solution_tracking['current_step']
        if remaining > 0:
            next_move = ui_state['solution_moves'][solution_tracking['current_step']]
            print(f"✓ Correct! Next move: {next_move} ({remaining} moves left)")
        else:
            print("✓ Solution complete! Well done!")
            solution_tracking['enabled'] = False
    else:
        # Wrong move - determine correction needed
        solution_tracking['move_feedback']['color'] = 'red'
        solution_tracking['move_feedback']['display_time'] = time.time()

        # Calculate needed correction moves
        correction_move = None
        correction_count = 0

        if move.endswith("'"):  # If wrong move was prime
            correction_move = move[0]  # Need normal move
            correction_count = 1
        elif move.endswith("2"):  # If wrong move was double
            correction_move = move[0]  # Need two normal moves
            correction_count = 2
        else:  # If wrong move was normal
            correction_move = move + "'"  # Need prime move
            correction_count = 1

        # Store correction information
        solution_tracking['wrong_move_correction'] = {
            'move': correction_move,
            'needed': correction_count,
            'count': 0
        }

        print(f"✗ Wrong move! Expected: {expected_move}")
        print(f"Make {correction_count} {correction_move} moves to correct position")

def update_move_feedback():
    """Update move feedback color timing"""
    if solution_tracking['move_feedback']['color'] != 'white':
        elapsed = time.time() - solution_tracking['move_feedback']['display_time']
        if elapsed >= solution_tracking['move_feedback']['duration']:
            solution_tracking['move_feedback']['color'] = 'white'

def commit_face_rotation(face, clockwise=True):
    """Apply face rotation to cube state"""
    face_cubelets = get_face_cubelets(face)
    axis = get_face_axis(face)

    # Rotate positions
    for cubelet in face_cubelets:
        cubelet.pos = rotate_position(cubelet.pos, axis, clockwise)
        cubelet.rotate_stickers(axis, clockwise)

    if (is_cube_solved() and
        game_state['scrambled'] and
        not ui_state['celebration']['active'] and
        game_state['move_count'] > 0):
        start_celebration()

def update_animation():
    """Update current animation"""
    global current_animation, move_queue

    # Don't animate if menu is showing
    if ui_state['show_menu']:
        glutPostRedisplay()
        return

    update_celebration()
    update_move_feedback()

    # Start new animation if queue not empty and not currently animating
    if current_animation is None and move_queue:
        move = move_queue.pop(0)
        current_animation = {
            'face': move['face'],
            'clockwise': move['clockwise'],
            'target_angle': move['angle'],
            'current_angle': 0
        }



    # Update current animation
    if current_animation is not None:
        current_animation['current_angle'] += ui_state['animation_speed']

        # Animation completed
        if current_animation['current_angle'] >= current_animation['target_angle']:
            # Commit the move
            if current_animation['target_angle'] == 180:
                # Double move - apply twice
                commit_face_rotation(current_animation['face'], current_animation['clockwise'])
                commit_face_rotation(current_animation['face'], current_animation['clockwise'])
            else:
                commit_face_rotation(current_animation['face'], current_animation['clockwise'])

            current_animation = None

    glutPostRedisplay()

def mouse_handler(button, state, x, y):
    """Handle mouse input"""
    global mouse_state

    if ui_state['show_menu']:
        return

    if button == GLUT_LEFT_BUTTON:
        if state == GLUT_DOWN:
            mouse_state['dragging'] = True
            mouse_state['last_x'] = x
            mouse_state['last_y'] = y
        elif state == GLUT_UP:
            mouse_state['dragging'] = False

    elif button == 3:  # Mouse wheel up
        camera['distance'] = max(200, camera['distance'] - 20)
        glutPostRedisplay()
    elif button == 4:  # Mouse wheel down
        camera['distance'] = min(800, camera['distance'] + 20)
        glutPostRedisplay()

def mouse_motion(x, y):
    """Handle mouse motion"""
    if mouse_state['dragging'] and not ui_state['show_menu']:
        dx = x - mouse_state['last_x']
        dy = y - mouse_state['last_y']

        camera['yaw'] += dx * 0.5
        camera['pitch'] -= dy * 0.5

        # Clamp pitch
        camera['pitch'] = max(-90, min(90, camera['pitch']))

        mouse_state['last_x'] = x
        mouse_state['last_y'] = y

        glutPostRedisplay()

# Global variable to track double move state
double_move_pending = False

def keyboard_handler(key, x, y):
    """Handle keyboard input with 4x4 support"""
    global double_move_pending

    if ui_state['show_menu']:
        if key == b'\r' or key == b'\n':  # Enter key
            if ui_state['menu_stage'] == 'cube_size':
                # Move to difficulty selection
                ui_state['menu_stage'] = 'difficulty'
                ui_state['difficulty_selection'] = 0
                glutPostRedisplay()
            else:  # difficulty stage
                # Confirm selection and start game
                cube_sizes = [2, 3, 4]
                selected_cube_size = cube_sizes[ui_state['menu_selection']]
                difficulties = ['Easy', 'Medium', 'Hard']
                global current_difficulty
                current_difficulty = difficulties[ui_state['difficulty_selection']]

                # Setup and start game
                setup_cube_size(selected_cube_size)
                init_cube()
                ui_state['show_menu'] = False
                ui_state['menu_stage'] = 'cube_size'  # Reset for next time
                game_state['cube_selected'] = True

                # Reset game state
                game_state['move_history'] = []
                game_state['move_count'] = 0
                game_state['timer_running'] = False
                game_state['scrambled'] = False
                game_state['solved_by_moves'] = False
                game_state['final_time'] = 0
                ui_state['last_move'] = None
                ui_state['celebration']['active'] = False
                ui_state['solution_moves'] = []
                ui_state['show_solution'] = False
                move_queue.clear()

                print(f"{cube_config['size']}x{cube_config['size']} cube selected with {current_difficulty} difficulty!")
                glutPostRedisplay()
            return

        elif key == b'\x08':  # Backspace key
            if ui_state['menu_stage'] == 'difficulty':
                # Go back to cube size selection
                ui_state['menu_stage'] = 'cube_size'
                glutPostRedisplay()
            return
        else:
            return

    key_char = key.decode('utf-8').upper()

    # Face rotations
    if key_char in 'UDLRFB' and game_state['cube_selected']:
        modifiers = glutGetModifiers()

        if double_move_pending:
            # Execute double move
            rotate_face(key_char, clockwise=True, double=True)
            double_move_pending = False
            print(f"Double move: {key_char}2")
        elif modifiers & GLUT_ACTIVE_SHIFT:
            # Prime move
            rotate_face(key_char, clockwise=False)
        else:
            # Normal move
            rotate_face(key_char, clockwise=True)

    # Double moves (press 2 then face key)
    elif key_char == '2':
        double_move_pending = True
        print("Double move mode - press face key (U/D/L/R/F/B)")

    # Scramble
    elif key_char == 'S' and game_state['cube_selected']:
        double_move_pending = False  # Reset double move state
        scramble_cube()

    # Reset
    elif key == b' ' and game_state['cube_selected']:
        double_move_pending = False  # Reset double move state
        init_cube()
        game_state['move_history'] = []
        game_state['move_count'] = 0
        game_state['timer_running'] = False
        game_state['scrambled'] = False
        game_state['solved_by_moves'] = False
        game_state['final_time'] = 0
        ui_state['last_move'] = None
        ui_state['celebration']['active'] = False

        ui_state['solution_moves'] = []
        ui_state['show_solution'] = False
        move_queue.clear()
        print(f"{cube_config['size']}x{cube_config['size']} cube reset!")

    # Toggle timer
    elif key_char == 'T' and game_state['cube_selected']:
        double_move_pending = False  # Reset double move state
        if game_state['timer_running']:
            game_state['timer_running'] = False
        else:
            game_state['timer_start'] = time.time()
            game_state['timer_running'] = True

    # Toggle help
    elif key_char == 'H':
        double_move_pending = False  # Reset double move state
        ui_state['show_help'] = not ui_state['show_help']

    # Back to menu
    elif key_char == 'M':
        double_move_pending = False  # Reset double move state
        ui_state['show_menu'] = True
        ui_state['menu_stage'] = 'cube_size'
        game_state['cube_selected'] = False
        ui_state['show_help'] = False
        print("Returned to menu")

    # Speed control
    elif key_char == '+':
        double_move_pending = False  # Reset double move state
        ui_state['animation_speed'] = min(20, ui_state['animation_speed'] + 1)
        print(f"Animation speed: {ui_state['animation_speed']}")
    elif key_char == '-':
        double_move_pending = False  # Reset double move state
        ui_state['animation_speed'] = max(1, ui_state['animation_speed'] - 1)
        print(f"Animation speed: {ui_state['animation_speed']}")

    # Show solution
    elif key_char == 'V' and game_state['cube_selected']:  # 'V' for View solution
        double_move_pending = False  # Reset double move state
        show_solution()

    # Hide solution
    elif key_char == 'C' and game_state['cube_selected']:  # 'C' to Clear solution display
        double_move_pending = False  # Reset double move state
        ui_state['show_solution'] = False
        ui_state['solution_moves'] = []
        print("Solution hidden")

    # Enable/Disable solution tracking
    elif key_char == 'E' and game_state['cube_selected']:
        double_move_pending = False  # Reset double move state
        if solution_tracking['enabled']:
            disable_solution_tracking()
        else:
            enable_solution_tracking()

    # Any other key resets double move state
    else:
        double_move_pending = False

def special_keys_handler(key, x, y):
    """Handle special keys (arrows, etc.) with 4x4 support"""
    if ui_state['show_menu']:
        if ui_state['menu_stage'] == 'cube_size':
            if key == GLUT_KEY_UP:
                ui_state['menu_selection'] = max(0, ui_state['menu_selection'] - 1)
                glutPostRedisplay()
            elif key == GLUT_KEY_DOWN:
                ui_state['menu_selection'] = min(2, ui_state['menu_selection'] + 1)  # Now 0, 1, 2 for 2x2, 3x3, 4x4
                glutPostRedisplay()

        elif ui_state['menu_stage'] == 'difficulty':
            if key == GLUT_KEY_UP:
                ui_state['difficulty_selection'] = max(0, ui_state['difficulty_selection'] - 1)
                glutPostRedisplay()
            elif key == GLUT_KEY_DOWN:
                ui_state['difficulty_selection'] = min(2, ui_state['difficulty_selection'] + 1)
                glutPostRedisplay()

    glutPostRedisplay()


def handle_enter_key():
    """Handle Enter key press for menu selection"""
    if ui_state['show_menu']:
        # Confirm selection
        if ui_state['menu_selection'] == 0:
            setup_cube_size(2)
        else:
            setup_cube_size(3)

        init_cube()
        ui_state['show_menu'] = False
        game_state['cube_selected'] = True

        # Reset game state
        game_state['move_history'] = []
        game_state['move_count'] = 0
        game_state['timer_running'] = False
        game_state['scrambled'] = False
        ui_state['last_move'] = None
        move_queue.clear()

        print(f"{cube_config['size']}x{cube_config['size']} cube selected!")
        glutPostRedisplay()

def display():
    """Main display function"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    if ui_state['show_menu']:
        draw_menu()
    else:
        setup_camera()
        setup_lighting()

        if ui_state['celebration']['active']:
          glRotatef(ui_state['celebration']['cube_spin'], 0, 1, 1)
        # Draw cube
        draw_animated_cube()

        if ui_state['celebration']['active']:
            draw_celebration_message()
        # Draw UI
        draw_ui()

    glutSwapBuffers()

def init_opengl():
    """Initialize OpenGL settings"""
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glClearColor(0.2, 0.2, 0.2, 1.0)

    # Enable smooth shading
    glShadeModel(GL_SMOOTH)

    # DISABLE face culling to fix the black face issue
    # Face culling was hiding faces that should be visible from certain angles
    glDisable(GL_CULL_FACE)

    # Enable normalization of normals (important for lighting)
    glEnable(GL_NORMALIZE)

    # Improve color blending
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

def main():
    """Main function"""
    # Initialize GLUT
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(window_width, window_height)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(cube_title)

    # Initialize OpenGL
    init_opengl()

    # Set callbacks
    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard_handler)
    glutSpecialFunc(special_keys_handler)
    glutMouseFunc(mouse_handler)
    glutMotionFunc(mouse_motion)
    glutIdleFunc(update_animation)

    print("3D Rubik's Cube Simulator")
    print("Use UP/DOWN arrows to select cube size, then press ENTER")

    # Start main loop
    glutMainLoop()

if __name__ == "__main__":
    main()
