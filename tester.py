#!/usr/bin/env python3
"""
tester.py - local tester for Ex1 (lexer for the language L).

Run it from the repository root:
    python3 tester.py                   # build ex1 and run all tests
    python3 tester.py 327772042/ex1     # explicit path to the ex1 folder
    python3 tester.py -k INT            # run only tests whose name contains "INT"
"""
import argparse
import difflib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

DEFAULT_EX1 = "327772042/ex1"   # folder that goes into the submission zip
TIMEOUT_SEC = 10                # self-check kills a single test after 10 seconds
JOBS = 4                        # nova is a shared server: run only a few JVMs at once
ERR = "ERROR"                   # the whole output file on any lexical error

TESTS = []      # (name, source text, expected output) - must match exactly
DISPUTED = []   # (name, source text, possible answers) - spec is ambiguous, only shown


def test(name, source, expected):
    """Register a test whose expected output follows directly from the spec."""
    TESTS.append((name, source, expected))


def disputed(name, source, options):
    """Register a case where the spec allows more than one reading."""
    DISPUTED.append((name, source, options))


def out(*tokens):
    """Build an expected output: one token per line, no trailing newline."""
    return "\n".join(tokens)


# ---------------------------------------------------------------------------
# Keywords and identifiers
# ---------------------------------------------------------------------------
test("KW01_all_keywords",
     "array class extends new nil if else while return int string void and or\n",
     out("ARRAY[1,1]", "CLASS[1,7]", "EXTENDS[1,13]", "NEW[1,21]", "NIL[1,25]",
         "IF[1,29]", "ELSE[1,32]", "WHILE[1,37]", "RETURN[1,43]", "TYPE_INT[1,50]",
         "TYPE_STRING[1,54]", "TYPE_VOID[1,61]", "AND[1,66]", "OR[1,70]"))
# Longest match: "iffy" is one ID, not IF + ID(fy)
test("KW02_keyword_prefix_is_id", "iffy classes int1 andy oral\n",
     out("ID(iffy)[1,1]", "ID(classes)[1,6]", "ID(int1)[1,14]", "ID(andy)[1,19]",
         "ID(oral)[1,24]"))
# Keywords are case sensitive
test("KW03_case_sensitive", "If CLASS Int Void\n",
     out("ID(If)[1,1]", "ID(CLASS)[1,4]", "ID(Int)[1,10]", "ID(Void)[1,14]"))
test("KW04_keyword_suffix_is_id", "xif myclass aand oor zint ostring\n",
     out("ID(xif)[1,1]", "ID(myclass)[1,5]", "ID(aand)[1,13]", "ID(oor)[1,18]",
         "ID(zint)[1,22]", "ID(ostring)[1,27]"))
test("KW05_keywords_next_to_punct", "if(x)return;while{nil}else[int]\n",
     out("IF[1,1]", "LPAREN[1,3]", "ID(x)[1,4]", "RPAREN[1,5]", "RETURN[1,6]",
         "SEMICOLON[1,12]", "WHILE[1,13]", "LBRACE[1,18]", "NIL[1,19]", "RBRACE[1,22]",
         "ELSE[1,23]", "LBRACK[1,27]", "TYPE_INT[1,28]", "RBRACK[1,31]"))
test("KW06_and_or", "a and b or c\nx and(y)or z\n",
     out("ID(a)[1,1]", "AND[1,3]", "ID(b)[1,7]", "OR[1,9]", "ID(c)[1,12]",
         "ID(x)[2,1]", "AND[2,3]", "LPAREN[2,6]", "ID(y)[2,7]", "RPAREN[2,8]",
         "OR[2,9]", "ID(z)[2,12]"))
test("KW07_glued_keywords_are_one_id", "ifelse whileif andor\n",
     out("ID(ifelse)[1,1]", "ID(whileif)[1,8]", "ID(andor)[1,16]"))
# In L an identifier is letters and digits only - no underscore
test("KW08_underscore_in_id", "a_b\n", ERR)
test("KW09_leading_underscore", "_x\n", ERR)
test("KW10_dollar_in_id", "my$var\n", ERR)

# ---------------------------------------------------------------------------
# Integers: 0 .. 2^15-1, no leading zeros, minus is a separate token
# ---------------------------------------------------------------------------
test("INT01_zero", "0", "INT(0)[1,1]")
test("INT02_max_32767", "32767", "INT(32767)[1,1]")
test("INT03_32768_out_of_range", "32768", ERR)
test("INT04_int32_max", "2147483647", ERR)
test("INT05_bigger_than_int32", "2147483648", ERR)   # Integer.valueOf would throw
test("INT06_huge", "99999999999999999999999999", ERR)
test("INT07_double_zero", "00", ERR)
test("INT08_leading_zero_007", "007", ERR)
test("INT09_leading_zero_032767", "032767", ERR)
test("INT10_leading_zero_in_code", "x := 01;\n", ERR)
test("INT11_leading_zero_last_line", "int x := 1;\nint y := 2;\nint z := 08;\n", ERR)
test("INT12_leading_zero_then_dot", "00.5\n", ERR)
test("INT13_zeros_separated", "0 0 0\n", out("INT(0)[1,1]", "INT(0)[1,3]", "INT(0)[1,5]"))
test("INT14_negatives_are_minus", "-5 -0 -32767\n",
     out("MINUS[1,1]", "INT(5)[1,2]", "MINUS[1,4]", "INT(0)[1,5]", "MINUS[1,7]",
         "INT(32767)[1,8]"))
test("INT15_minus_32768", "-32768\n", ERR)           # 32768 itself is out of range
test("INT16_decimal_points", "3.14 .5 5.\n",
     out("INT(3)[1,1]", "DOT[1,2]", "INT(14)[1,3]", "DOT[1,6]", "INT(5)[1,7]",
         "INT(5)[1,9]", "DOT[1,10]"))
test("INT17_zero_next_to_punct", "0;0)0+0\n",
     out("INT(0)[1,1]", "SEMICOLON[1,2]", "INT(0)[1,3]", "RPAREN[1,4]", "INT(0)[1,5]",
         "PLUS[1,6]", "INT(0)[1,7]"))
test("INT18_out_of_range_after_valid_code", "int x := 5;\nint y := 40000;\n", ERR)

# ---------------------------------------------------------------------------
# Strings: letters only between double quotes, value printed WITH the quotes
# ---------------------------------------------------------------------------
test("STR01_simple", '"Dan"', 'STRING("Dan")[1,1]')
test("STR02_empty", '""', 'STRING("")[1,1]')
test("STR03_space_inside", '"a b"\n', ERR)
test("STR04_digit_inside", '"a1"\n', ERR)
test("STR05_comma_inside", '"a,b"\n', ERR)
test("STR06_underscore_inside", '"a_b"\n', ERR)
test("STR07_tab_inside", '"a\tb"\n', ERR)
test("STR08_unclosed_at_eof", '"abc', ERR)
test("STR09_unclosed_newline", '"abc\n"\n', ERR)
test("STR10_lone_quote", '"', ERR)
test("STR11_escaped_quote", '"a\\"b"\n', ERR)
test("STR12_three_quotes", '"""\n', ERR)
test("STR13_adjacent_strings", '"ab""cd"\n', out('STRING("ab")[1,1]', 'STRING("cd")[1,5]'))
test("STR14_four_quotes", '""""\n', out('STRING("")[1,1]', 'STRING("")[1,3]'))
test("STR15_string_then_id", '"abc"def\n', out('STRING("abc")[1,1]', "ID(def)[1,6]"))
test("STR16_id_then_string", 'abc"def"\n', out("ID(abc)[1,1]", 'STRING("def")[1,4]'))
test("STR17_keyword_inside_string", '"if" "class"\n',
     out('STRING("if")[1,1]', 'STRING("class")[1,6]'))
test("STR18_in_program", 'string s := "Hello";\nPrintString(s);\n',
     out("TYPE_STRING[1,1]", "ID(s)[1,8]", "ASSIGN[1,10]", 'STRING("Hello")[1,13]',
         "SEMICOLON[1,20]", "ID(PrintString)[2,1]", "LPAREN[2,12]", "ID(s)[2,13]",
         "RPAREN[2,14]", "SEMICOLON[2,15]"))
test("STR19_unclosed_at_end_of_program", 'int x := 1;\nstring s := "oops;\n', ERR)

# ---------------------------------------------------------------------------
# Type-1 comments: // ... up to the first newline
# ---------------------------------------------------------------------------
test("C1_01_simple", "// hello world\nx", "ID(x)[2,1]")
test("C1_02_empty_comment", "//\nx", "ID(x)[2,1]")
test("C1_03_all_allowed_chars",
     "// abcXYZ 0123456789 ( ) [ ] { } ? ! + - * / . ;\t\nx", "ID(x)[2,1]")
test("C1_04_after_code", "x := 1; // set x\ny := 2;\n",
     out("ID(x)[1,1]", "ASSIGN[1,3]", "INT(1)[1,6]", "SEMICOLON[1,7]",
         "ID(y)[2,1]", "ASSIGN[2,3]", "INT(2)[2,6]", "SEMICOLON[2,7]"))
test("C1_05_contains_block_start", "// /* not a block\nx\n", "ID(x)[2,1]")
test("C1_06_contains_block_end", "// */\nx\n", "ID(x)[2,1]")
test("C1_07_line_numbers", "a\n// c\nb\n// d\n\nc\n",
     out("ID(a)[1,1]", "ID(b)[3,1]", "ID(c)[6,1]"))
test("C1_08_no_space_before", "x//c\ny", out("ID(x)[1,1]", "ID(y)[2,1]"))
test("C1_09_comment_only_file", "// only a comment\n", "")
# Commenting out code with := is an error, because ':' and '=' are not allowed
test("C1_10_commented_assign", "void main()\n{\n    // x := 5;\n}\n", ERR)
test("C1_11_commented_call_ok", "// PrintInt(x+1);\nx\n", "ID(x)[2,1]")
test("C1_12_bad_char_after_valid_lines", "int x := 1;\nint y := 2;\n// what: now\n", ERR)

# ---------------------------------------------------------------------------
# Type-2 comments: /* ... */  (not nested, may span lines)
# ---------------------------------------------------------------------------
test("C2_01_simple", "/* hello */x", "ID(x)[1,12]")
test("C2_02_empty", "/**/x", "ID(x)[1,5]")
test("C2_03_three_stars", "/***/x", "ID(x)[1,6]")
test("C2_04_slash_inside", "/*/ */x", "ID(x)[1,7]")
test("C2_05_stars_before_close", "/* a **/x", "ID(x)[1,9]")
test("C2_06_multiline", "/* line1\nline2\n   line3 */ x", "ID(x)[3,13]")
test("C2_07_all_allowed_chars",
     "/* abcXYZ 0123456789 ( ) [ ] { } ? ! + - * / . ;\t\n */x", "ID(x)[2,4]")
test("C2_08_unclosed", "/* abc", ERR)
test("C2_09_unclosed_star", "/* abc *", ERR)
test("C2_10_only_open", "/*", ERR)
test("C2_11_open_then_slash", "/*/", ERR)    # the '*' of "/*" cannot be reused for "*/"
test("C2_12_unclosed_after_code", "int x := 1;\n/* never closed\n", ERR)
test("C2_13_not_nested", "/* a /* b */ c */", out("ID(c)[1,14]", "TIMES[1,16]", "DIVIDE[1,17]"))
test("C2_14_close_without_open", "a*/", out("ID(a)[1,1]", "TIMES[1,2]", "DIVIDE[1,3]"))
test("C2_15_between_tokens", "x/**/y", out("ID(x)[1,1]", "ID(y)[1,6]"))
test("C2_16_bad_char_on_later_line", "/* ok\nok\nbad, */\nx\n", ERR)
test("C2_17_columns_after_multiline", "/*\n*/x y\n", out("ID(x)[2,3]", "ID(y)[2,5]"))
test("C2_18_divide_space_times", "a / *b\n",
     out("ID(a)[1,1]", "DIVIDE[1,3]", "TIMES[1,5]", "ID(b)[1,6]"))
test("C2_19_commented_assign", "/* x := 3; */\n", ERR)

# Characters that are illegal inside comments (comma, colon, = < > are legal in code!)
BAD_IN_COMMENT = [",", ":", "=", "<", ">", '"', "'", "_", "@", "#", "$", "%",
                  "^", "&", "|", "\\", "~", "`", "\u05d0"]   # last one is a Hebrew letter
for i, ch in enumerate(BAD_IN_COMMENT):
    test(f"C1_BAD_{i:02d}_{ascii(ch)}", f"x := 1; // bad{ch}char\ny\n", ERR)
    test(f"C2_BAD_{i:02d}_{ascii(ch)}", f"x := 1; /* bad{ch}char */ y\n", ERR)

# ---------------------------------------------------------------------------
# Operators and punctuation
# ---------------------------------------------------------------------------
test("OP01_all_single", "+ - * / = < > ( ) [ ] { } , . ;\n",
     out("PLUS[1,1]", "MINUS[1,3]", "TIMES[1,5]", "DIVIDE[1,7]", "EQ[1,9]", "LT[1,11]",
         "GT[1,13]", "LPAREN[1,15]", "RPAREN[1,17]", "LBRACK[1,19]", "RBRACK[1,21]",
         "LBRACE[1,23]", "RBRACE[1,25]", "COMMA[1,27]", "DOT[1,29]", "SEMICOLON[1,31]"))
test("OP02_all_without_spaces", "+-*=<>()[]{},.;:=\n",
     out("PLUS[1,1]", "MINUS[1,2]", "TIMES[1,3]", "EQ[1,4]", "LT[1,5]", "GT[1,6]",
         "LPAREN[1,7]", "RPAREN[1,8]", "LBRACK[1,9]", "RBRACK[1,10]", "LBRACE[1,11]",
         "RBRACE[1,12]", "COMMA[1,13]", "DOT[1,14]", "SEMICOLON[1,15]", "ASSIGN[1,16]"))
test("OP03_assign_no_spaces", "x:=y\n", out("ID(x)[1,1]", "ASSIGN[1,2]", "ID(y)[1,4]"))
test("OP04_colon_alone", ":\n", ERR)
test("OP05_colon_space_equals", "x : = 1;\n", ERR)
test("OP06_assign_then_eq", ":==\n", out("ASSIGN[1,1]", "EQ[1,3]"))
test("OP07_eq_then_colon", "=:\n", ERR)
test("OP08_double_eq", "==\n", out("EQ[1,1]", "EQ[1,2]"))
test("OP09_le_ge_are_two_tokens", "<= >=\n", out("LT[1,1]", "EQ[1,2]", "GT[1,4]", "EQ[1,5]"))
test("OP10_not_equal", "a != b\n", ERR)
test("OP11_five_pluses", "x+++++y\n",
     out("ID(x)[1,1]", "PLUS[1,2]", "PLUS[1,3]", "PLUS[1,4]", "PLUS[1,5]", "PLUS[1,6]",
         "ID(y)[1,7]"))
test("OP12_double_assign", ":=:=\n", out("ASSIGN[1,1]", "ASSIGN[1,3]"))
test("OP13_assign_split_by_newline", "x :\n= 1;\n", ERR)
for ch in ["!", "?", "&", "|", "%", "^", "~", "`", "@", "#", "$", "\\", "'"]:
    test(f"OP_BAD_{ascii(ch)}", f"x := a {ch} b;\n", ERR)

# ---------------------------------------------------------------------------
# Whitespace and positions
# ---------------------------------------------------------------------------
test("WS01_empty_file", "", "")
test("WS02_only_whitespace", "   \n\t\n  ", "")
test("WS03_leading_spaces", "     x", "ID(x)[1,6]")
test("WS04_tab_is_one_column", "\tx\t\ty", out("ID(x)[1,2]", "ID(y)[1,5]"))
test("WS05_blank_lines", "\n\n\nx\n\n y", out("ID(x)[4,1]", "ID(y)[6,2]"))
test("WS06_no_trailing_newline", "x", "ID(x)[1,1]")
test("WS07_mixed_whitespace", " \t \n\t x \t\n", "ID(x)[2,3]")
test("WS08_indented_block", "{\n    x;\n        y;\n}\n",
     out("LBRACE[1,1]", "ID(x)[2,5]", "SEMICOLON[2,6]", "ID(y)[3,9]", "SEMICOLON[3,10]",
         "RBRACE[4,1]"))
test("WS09_column_100", " " * 99 + "x\n", "ID(x)[1,100]")

# ---------------------------------------------------------------------------
# Error placement: the output must be ONLY "ERROR", no partial token list
# ---------------------------------------------------------------------------
test("ERR01_first_char", "$x := 5;\n", ERR)
test("ERR02_middle", "x := 5;\ny := @;\nz := 6;\n", ERR)
test("ERR03_last_char", "x := 5;$", ERR)
test("ERR04_hebrew_in_code", "x := \u05e9\u05dc\u05d5\u05dd;\n", ERR)
test("ERR05_emoji", "x := 1; \U0001F600\n", ERR)
test("ERR06_null_byte", "x\0y\n", ERR)
test("ERR07_after_comment", "/* fine */ x := 1; ?\n", ERR)
test("ERR08_accented_letter", "caf\u00e9 := 1;\n", ERR)

# ---------------------------------------------------------------------------
# Big input (built from a block whose tokens we know, line numbers shifted)
# ---------------------------------------------------------------------------
BLOCK = "int x := 1;\nwhile (x < 32767) { x := x * 2; }\n"
BLOCK_TOKENS = [  # (line inside block, column, token text)
    (1, 1, "TYPE_INT"), (1, 5, "ID(x)"), (1, 7, "ASSIGN"), (1, 10, "INT(1)"),
    (1, 11, "SEMICOLON"), (2, 1, "WHILE"), (2, 7, "LPAREN"), (2, 8, "ID(x)"),
    (2, 10, "LT"), (2, 12, "INT(32767)"), (2, 17, "RPAREN"), (2, 19, "LBRACE"),
    (2, 21, "ID(x)"), (2, 23, "ASSIGN"), (2, 26, "ID(x)"), (2, 28, "TIMES"),
    (2, 30, "INT(2)"), (2, 31, "SEMICOLON"), (2, 33, "RBRACE"),
]
REPEAT = 5000   # 10,000 lines, 95,000 tokens
big_expected = out(*(f"{tok}[{k * 2 + ln},{col}]"
                     for k in range(REPEAT) for ln, col, tok in BLOCK_TOKENS))
test("BIG01_10k_lines", BLOCK * REPEAT, big_expected)
test("BIG02_10k_lines_error_at_end", BLOCK * REPEAT + "$\n", ERR)
test("BIG03_50k_blank_lines", "\n" * 50000 + "x\n", "ID(x)[50001,1]")

# ---------------------------------------------------------------------------
# Disputed: the spec can be read in two ways - ask on the course forum
# ---------------------------------------------------------------------------
disputed("D1_line_comment_at_eof", "x := 1; // done",
         ["ERROR",
          out("ID(x)[1,1]", "ASSIGN[1,3]", "INT(1)[1,6]", "SEMICOLON[1,7]",
              "DIVIDE[1,9]", "DIVIDE[1,10]", "ID(done)[1,12]")])
disputed("D2_only_comment_no_newline", "// abc",
         ["ERROR", out("DIVIDE[1,1]", "DIVIDE[1,2]", "ID(abc)[1,4]")])
disputed("D3_digit_then_letters", "3oranges\n",
         [out("INT(3)[1,1]", "ID(oranges)[1,2]"), "ERROR"])


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build(ex1):
    """Run make without a terminal (TERM not set), then with one if only `clear` failed.

    Returns True if make works without a terminal. The course skeleton's Makefile
    starts with `clear`, which fails when TERM is not set - so this is only a note.
    """
    lexer = os.path.join(ex1, "LEXER")
    if os.path.exists(lexer):
        os.remove(lexer)            # make sure we test a fresh build
    env = dict(os.environ)
    env.pop("TERM", None)
    p = subprocess.run(["make"], cwd=ex1, env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
    makefile_ok = p.returncode == 0
    if not makefile_ok:
        if "TERM environment variable not set" not in p.stdout:
            print(p.stdout[-3000:])
            sys.exit("make FAILED - fix the build first")
        # Build again with a terminal type so the remaining tests can still run
        env["TERM"] = os.environ.get("TERM", "xterm")
        p = subprocess.run(["make"], cwd=ex1, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
        if p.returncode != 0:
            print(p.stdout[-3000:])
            sys.exit("make FAILED - fix the build first")
    if not os.path.isfile(lexer):
        sys.exit("make finished but ex1/LEXER was not created")
    return makefile_ok


# ---------------------------------------------------------------------------
# Submission checks (things self-check does not test, but the zip needs)
# ---------------------------------------------------------------------------
def submission_checks(ex1):
    """Return (problems, notes): problems break the submission, notes are advice."""
    problems, notes = [], []
    if os.path.basename(ex1) != "ex1":
        problems.append("the code folder must be called 'ex1' (zip = ids.txt + ex1/)")
    ids = os.path.join(os.path.dirname(ex1), "ids.txt")
    if not os.path.isfile(ids):
        problems.append(f"no ids.txt next to the ex1 folder (expected {ids})")
    else:
        with open(ids, "r", errors="replace") as f:
            lines = [ln.strip() for ln in f.read().splitlines() if ln.strip()]
        if not lines or not all(ln.isdigit() for ln in lines):
            problems.append("ids.txt must contain only IDs, one per line")
        elif len(lines) == 1:
            notes.append("ids.txt has only 1 ID - add every team member, one per line")
    return problems, notes


# ---------------------------------------------------------------------------
# Run one test exactly like self-check.py does
# ---------------------------------------------------------------------------
def run_lexer(ex1, workdir, name, source):
    """Write the source to a file, run the jar, return (status, output, seconds)."""
    inp = os.path.join(workdir, name + ".txt")
    res = os.path.join(workdir, name + ".out")
    with open(inp, "w", encoding="utf-8", newline="") as f:
        f.write(source)     # newline="" keeps the text byte-for-byte
    start = time.time()
    try:
        p = subprocess.run(["java", "-jar", os.path.abspath(os.path.join(ex1, "LEXER")),
                            inp, res], cwd=ex1, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", f"no result after {TIMEOUT_SEC} seconds", TIMEOUT_SEC
    seconds = time.time() - start
    if p.returncode != 0:
        return "CRASH", p.stderr.decode(errors="replace")[-1500:], seconds
    if not os.path.isfile(res):
        return "FAIL", "no output file was written", seconds
    with open(res, "r", encoding="utf-8", errors="replace") as f:
        return "RAN", f.read(), seconds


def check(ex1, workdir, name, source, expected):
    status, got, seconds = run_lexer(ex1, workdir, name, source)
    if status != "RAN":
        return name, status, got, seconds
    if got == expected:
        return name, "OK", "", seconds
    if got.rstrip("\n") == expected.rstrip("\n"):
        return name, "FAIL", "only the newline at the end of the file differs", seconds
    diff = difflib.unified_diff(expected.splitlines(), got.splitlines(),
                                "expected", "your lexer", n=1, lineterm="")
    return name, "FAIL", "\n".join(list(diff)[:30]), seconds


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ex1", nargs="?", default=DEFAULT_EX1, help="path to the ex1 folder")
    ap.add_argument("-k", default="", help="run only tests whose name contains this text")
    args = ap.parse_args()
    ex1 = os.path.abspath(args.ex1)
    if not os.path.isfile(os.path.join(ex1, "Makefile")):
        sys.exit(f"no Makefile in {ex1} - run from the repository root or pass the path")

    makefile_ok = build(ex1)
    problems, notes = submission_checks(ex1)
    if not makefile_ok:
        notes.append("Makefile: 'clear' fails without a terminal (same as the course "
                     "skeleton). Optional, harmless fix: '-clear'")
    selected = [t for t in TESTS if args.k in t[0]]
    workdir = tempfile.mkdtemp(prefix="ex1_tester_")
    try:
        with ThreadPoolExecutor(max_workers=JOBS) as pool:
            results = list(pool.map(lambda t: check(ex1, workdir, *t), selected))
        shown = [(n, s, o, run_lexer(ex1, workdir, n, s)[1])
                 for n, s, o in DISPUTED if args.k in n]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    failed = [r for r in results if r[1] != "OK"]
    for name, status, info, seconds in failed:
        print(f"\n[{status}] {name}")
        print("    " + info.replace("\n", "\n    "))
    for name, status, info, seconds in results:
        if name.startswith("BIG"):
            print(f"time {name}: {seconds:.2f}s (limit {TIMEOUT_SEC}s)")

    print("\n--- disputed cases (not counted, ask on the forum) ---")
    for name, source, options, got in shown:
        which = options.index(got) + 1 if got in options else None
        verdict = f"matches option {which}" if which else "matches NO known option!"
        print(f"{name}: {verdict}")
        print("    your lexer: " + (got.replace("\n", " | ") or "(empty output)"))

    print("\n=========== SUMMARY ===========")
    print(f"TESTS: {len(results) - len(failed)}/{len(results)} passed")
    for p in problems:
        print(f"PROBLEM: {p}")
    for n in notes:
        print(f"NOTE:    {n}")
    sys.exit(0 if not failed and not problems else 1)


if __name__ == "__main__":
    main()