# Incomplete dirty partial SVG path parser.
#
# SVG paths are annoying because the allow implicit repetition of the previous
# command, and also that negative numbers can serve as the delimter of the
# previous token (so, starting a new number without a comma or space in-between)
# (It seems like . can be as well but I'm not handling that because it's ridiculous.)
#

# Copy the path string into its own text file and pass it as an argument to this.
import sys
with open(sys.argv[1], 'r') as file:
    file_data = file.read()

OPERATIONS = 'cCsvVlLMz' # There are many more than this; these are just what I needed.
DELIMITERS = OPERATIONS + ', '

tokens = []
cur_token = ''

cursor_pos = [0.0, 0.0]

segments = []
lines = []
curves = []

def handle_c(cmd, args):
    # Takes 3 points per curve
    while len(args) != 0:
        x1 = args.pop(0)
        y1 = args.pop(0)
        if cmd == 'c':
            x1 += cursor_pos[0]
            y1 += cursor_pos[1]
        
        x2 = args.pop(0)
        y2 = args.pop(0)
        if cmd == 'c':
            x2 += cursor_pos[0]
            y2 += cursor_pos[1]
        
        x = args.pop(0)
        y = args.pop(0)
        if cmd == 'c':
            x += cursor_pos[0]
            y += cursor_pos[1]
        curves.append([cursor_pos[0], cursor_pos[1], x1, y1, x2, y2, x, y])
        segments.append(['c', cursor_pos[0], cursor_pos[1], x1, y1, x2, y2, x, y])
        handle_m('M', [x,y])        

# TODO: BUG: Both s and v should have while loops to handle multiple instances
# In fact it'd be a good idea to just factor the while loop out and have the
# handlers say how much they need but

def handle_s(cmd, args): # shortcut for curve
    if segments[-1][0] != 'c': raise 'unsupported shortcut curve'
    # Convert command to regular curve
    # Extract previous curve's last control point
    xp = segments[-1][5]
    yp = segments[-1][6]
    # Reverse them around the current position
    xr = 2*cursor_pos[0] - xp
    yr = 2*cursor_pos[1] - yp
    # Convert to absolute coordinates if required
    if cmd == 's':
        args[0] += cursor_pos[0]
        args[1] += cursor_pos[1]
        args[2] += cursor_pos[0]
        args[3] += cursor_pos[1]
    # And then pass it on to the regular curve
    cmd = 'C'
    handle_c(cmd, [xr, yr] + args)

def handle_v(cmd, args): # shortcut for vertical line
    if cmd == 'v':
        x = 0
        cmd = 'l'
    else:
        x = cursor_pos[0]
        cmd = 'L'
    for arg in args:
        handle_l(cmd, [x, arg])

def handle_l(cmd, args):
    '''Line-to command, either absolute or relative to current position'''
    while len(args) != 0:
        fr_x = cursor_pos[0]
        fr_y = cursor_pos[1]
        to_x = args.pop(0)
        to_y = args.pop(0)
        if cmd == 'l': # relative to current cursor
            to_x += cursor_pos[0]
            to_y += cursor_pos[1]
        
        line = [fr_x, fr_y, to_x, to_y]
        lines.append(line)
        segments.append(['l'] + line)
        handle_m('M', [to_x,to_y])

# TODO: BUG: Theoretically all the handlers should validate upper/lower case only
# and that would be another good thing to factor out
def handle_m(cmd, args):
    '''Move-to command. Moves cursor to new position without drawing a line.'''
    global cursor_pos
    if cmd == 'm': # relative to current position
        cursor_pos = [cursor_pos[0] + args[0], cursor_pos[1] + args[1]]
    elif cmd == 'M': # absolute
        cursor_pos = [args[0], args[1]]
    else:
        raise ''

handlers = {
    'c' : handle_c,
    's' : handle_s,
    'v' : handle_v,
    'l' : handle_l,
    'm' : handle_m
}

c_prev = ''
op_prev = ' '
for c in file_data: # c is each character one by one of the data

    #
    # Annoyingly, - is also sometimes a delimiter, and in that role it needs to
    # not be eaten, because it's also part of the number. And furthermore, it's
    # only a delimiter if the previous character is *not* a delimiter. If it was,
    # then it's just part of the number text and doesn't form a new token because
    # the previous character, which was a delimiter, just did that.
    #
    
    # If it's a delimiter, or the minus sign of a number is serving as one ...
    if (c in DELIMITERS) or ((c == '-') and (c_prev not in DELIMITERS)):
    
        # Store the accumulated token (without adding this delimiter to it {in
        # other words, eating this delimiter}) and start a new one.
        if cur_token != '': tokens.append(float(cur_token))
        cur_token = ''
        
        # Check if its a minus sign, which needs added to the new token.
        if c == '-':
            cur_token += c
        
        # Finally, operations also serve as delimiters, but not all delimiters
        # are operations (space and comma), so if it's an operation, handle it.
        if c in OPERATIONS:
            # At this point, tokens contains the data for one *or more repeated*
            # instances of the operation, which the handler needs to split.
            if op_prev in OPERATIONS:
                if op_prev.lower() in handlers:
                    handlers[op_prev.lower()](op_prev, tokens)
                else:
                    raise BaseException("Handler not found!")
            tokens = []
            op_prev = c

    # Otherwise, accumulate the text into the current token.
    else:
        cur_token += c

    c_prev = c

#for i, s in enumerate(segments):
#    print(i,s)

line_templ = '<wire x1="{}" y1="{}" x2="{}" y2="{}" width="0.1524" layer="20"/>'
curve_templ = '''<spline width="0.1524" layer="20" locked="no">
<vertex x="{}" y="{}"/>
<vertex x="{}" y="{}"/>
<vertex x="{}" y="{}"/>
<vertex x="{}" y="{}"/>
</spline>'''

for s in segments:
    if s[0] == 'l':
        print(line_templ.format(*[pt * 0.19 for pt in s[1:]]))
    elif s[0] == 'c':
        print(curve_templ.format(*[pt * 0.19 for pt in s[1:]]))
    else: raise 'unsupported line type'


