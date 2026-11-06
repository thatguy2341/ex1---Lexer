#!/usr/bin/env python3
"""
make_tests271.py - generates 271 tests for Ex1 in the official self-check format:
    tests271/tests/TEST_<NAME>.txt
    tests271/expected_output/TEST_<NAME>_Expected_Output.txt

Expected outputs come from a small reference lexer below, written directly from
the exercise PDF (it reproduces the 3 official tests byte for byte). Most tests
also have a hand-written expectation; the script refuses to write anything if a
hand-written expectation and the reference lexer disagree.

Usage (from the repository root):
    python3 make_tests271.py
"""
import os
import random
import shutil
import sys

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests271")


# ===========================================================================
# Reference lexer for L (from the spec)
# ===========================================================================
KEYWORDS = {
    "array": "ARRAY", "class": "CLASS", "extends": "EXTENDS", "new": "NEW",
    "nil": "NIL", "if": "IF", "else": "ELSE", "while": "WHILE",
    "return": "RETURN", "int": "TYPE_INT", "string": "TYPE_STRING",
    "void": "TYPE_VOID", "and": "AND", "or": "OR",
}
SINGLE = {
    "+": "PLUS", "-": "MINUS", "*": "TIMES", "/": "DIVIDE", "=": "EQ",
    "<": "LT", ">": "GT", "(": "LPAREN", ")": "RPAREN", "[": "LBRACK",
    "]": "RBRACK", "{": "LBRACE", "}": "RBRACE", ",": "COMMA", ".": "DOT",
    ";": "SEMICOLON",
}
LETTERS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
DIGITS = set("0123456789")
WS = set(" \t\n\r")
COMMENT_OK = LETTERS | DIGITS | WS | set("()[]{}?!+-*/.;")   # Figure 2
MAX_INT = 2 ** 15 - 1


class LexError(Exception):
    pass


def lex(text):
    """Return a list of output lines; raise LexError on any lexical error."""
    out, i, n, line, col = [], 0, len(text), 1, 1

    def advance(k):
        nonlocal i, line, col
        for _ in range(k):
            if text[i] == "\n":
                line, col = line + 1, 1
            else:
                col += 1
            i += 1

    def emit(name, length, value=None):
        out.append(f"{name}[{line},{col}]" if value is None
                   else f"{name}({value})[{line},{col}]")
        advance(length)

    while i < n:
        c = text[i]
        if c in WS:
            advance(1)
        elif text.startswith("//", i):                 # Type-1 comment
            j = text.find("\n", i)
            if j == -1:
                raise LexError("// without a newline before end of input")
            if any(ch not in COMMENT_OK for ch in text[i + 2:j]):
                raise LexError("illegal character in // comment")
            advance(j + 1 - i)
        elif text.startswith("/*", i):                 # Type-2 comment
            j = text.find("*/", i + 2)
            if j == -1:
                raise LexError("unclosed /* comment")
            if any(ch not in COMMENT_OK for ch in text[i + 2:j]):
                raise LexError("illegal character in /* comment")
            advance(j + 2 - i)
        elif c == '"':                                 # string: letters only
            j = i + 1
            while j < n and text[j] in LETTERS:
                j += 1
            if j >= n or text[j] != '"':
                raise LexError("bad or unclosed string")
            emit("STRING", j + 1 - i, text[i:j + 1])
        elif c in DIGITS:                              # integer
            j = i
            while j < n and text[j] in DIGITS:
                j += 1
            s = text[i:j]
            if (len(s) > 1 and s[0] == "0") or int(s) > MAX_INT:
                raise LexError("leading zero or out of range")
            emit("INT", j - i, s)
        elif c in LETTERS:                             # identifier / keyword
            j = i
            while j < n and (text[j] in LETTERS or text[j] in DIGITS):
                j += 1
            word = text[i:j]
            if word in KEYWORDS:
                emit(KEYWORDS[word], j - i)
            else:
                emit("ID", j - i, word)
        elif text.startswith(":=", i):
            emit("ASSIGN", 2)
        elif c in SINGLE:
            emit(SINGLE[c], 1)
        else:
            raise LexError(f"illegal character {c!r}")
    return out


def render(text):
    """What the output file must contain."""
    try:
        return "\n".join(lex(text))
    except LexError:
        return "ERROR"


# ===========================================================================
# Test definitions
# ===========================================================================
MAIN = []   # (name, input text, hand-written expected output or None)


def E(*lines):
    """Expected output: one token per line, no trailing newline."""
    return "\n".join(lines)


def t(name, text, expected=None):
    """Register a test. expected=None -> take it from the reference lexer."""
    MAIN.append((name, text, expected))


ERR = "ERROR"

# Characters that are illegal both in code and inside comments.
BAD_EVERYWHERE = {
    "Comma": ",", "Colon": ":", "Equals": "=", "Less": "<", "Greater": ">",
    "DQuote": '"', "SQuote": "'", "Underscore": "_", "At": "@", "Hash": "#",
    "Dollar": "$", "Percent": "%", "Caret": "^", "Amp": "&", "Pipe": "|",
    "Backslash": "\\", "Tilde": "~", "Backtick": "`", "Hebrew": "\u05d0",
}
# (comma, colon, =, <, > are legal tokens in code but illegal inside comments)

# =====================================================================
# KW: keywords and identifiers
# =====================================================================
t("KW01_All_Keywords",
  "array class extends new nil if else while return int string void and or\n",
  E("ARRAY[1,1]", "CLASS[1,7]", "EXTENDS[1,13]", "NEW[1,21]", "NIL[1,25]",
    "IF[1,29]", "ELSE[1,32]", "WHILE[1,37]", "RETURN[1,43]", "TYPE_INT[1,50]",
    "TYPE_STRING[1,54]", "TYPE_VOID[1,61]", "AND[1,66]", "OR[1,70]"))
t("KW02_Keyword_Prefix_Is_ID",
  "iffy classes int1 newer nils arrays elsewhere whiles returned integer strings voids andy oral\n",
  E("ID(iffy)[1,1]", "ID(classes)[1,6]", "ID(int1)[1,14]", "ID(newer)[1,19]",
    "ID(nils)[1,25]", "ID(arrays)[1,30]", "ID(elsewhere)[1,37]", "ID(whiles)[1,47]",
    "ID(returned)[1,54]", "ID(integer)[1,63]", "ID(strings)[1,71]", "ID(voids)[1,79]",
    "ID(andy)[1,85]", "ID(oral)[1,90]"))
t("KW03_Keywords_Case_Sensitive",
  "If CLASS Int Void WHILE Nil Return AND Or STRING Array ELSE New Extends\n")
t("KW04_Keyword_Suffix_Is_ID", "xif myclass aand oor zint ostring\n",
  E("ID(xif)[1,1]", "ID(myclass)[1,5]", "ID(aand)[1,13]", "ID(oor)[1,18]",
    "ID(zint)[1,22]", "ID(ostring)[1,27]"))
t("KW05_Keywords_Next_To_Punct", "if(x)return;while{nil}else[int]\n",
  E("IF[1,1]", "LPAREN[1,3]", "ID(x)[1,4]", "RPAREN[1,5]", "RETURN[1,6]",
    "SEMICOLON[1,12]", "WHILE[1,13]", "LBRACE[1,18]", "NIL[1,19]", "RBRACE[1,22]",
    "ELSE[1,23]", "LBRACK[1,27]", "TYPE_INT[1,28]", "RBRACK[1,31]"))
t("KW06_And_Or_Operators", "a and b or c\nx and(y)or z\n",
  E("ID(a)[1,1]", "AND[1,3]", "ID(b)[1,7]", "OR[1,9]", "ID(c)[1,12]",
    "ID(x)[2,1]", "AND[2,3]", "LPAREN[2,6]", "ID(y)[2,7]", "RPAREN[2,8]",
    "OR[2,9]", "ID(z)[2,12]"))
t("KW07_Identifiers_Variety", "a Z abc ABC aBc123 x0 z9y8 L i1j2k3\n")
t("KW08_Long_Identifier", "x" + "aB3" * 400 + "\n", "ID(x" + "aB3" * 400 + ")[1,1]")
t("KW09_Underscore_In_ID", "a_b\n", ERR)
t("KW10_Leading_Underscore", "_x\n", ERR)
t("KW11_Dollar_In_ID", "my$var\n", ERR)
t("KW12_Keywords_Glued", "ifelse whileif intvoid classextends andor\n",
  E("ID(ifelse)[1,1]", "ID(whileif)[1,8]", "ID(intvoid)[1,16]",
    "ID(classextends)[1,24]", "ID(andor)[1,37]"))
t("KW13_ID_With_Digits_Only_After", "a1 b22 c333 d0\n")
t("KW14_Single_Letters", "a b c d e f g h i j k l m n o p q r s t u v w x y z\n")

# =====================================================================
# INT: integers
# =====================================================================
t("INT01_Zero", "0", "INT(0)[1,1]")
t("INT02_Max_32767", "32767", "INT(32767)[1,1]")
t("INT03_Max_Plus_One_32768", "32768", ERR)
t("INT04_65535", "65535", ERR)
t("INT05_Int32_Max", "2147483647", ERR)
t("INT06_Int32_Max_Plus_One", "2147483648", ERR)
t("INT07_Huge_Number", "99999999999999999999999999", ERR)
t("INT08_Double_Zero", "00", ERR)
t("INT09_Leading_Zero_007", "007", ERR)
t("INT10_Leading_Zero_032767", "032767", ERR)
t("INT11_Leading_Zero_In_Assign", "x := 01;\n", ERR)
t("INT12_Zeros_Separated", "0 0 0\n", E("INT(0)[1,1]", "INT(0)[1,3]", "INT(0)[1,5]"))
t("INT13_Negatives_Are_Minus", "-5 -0 -32767\n",
  E("MINUS[1,1]", "INT(5)[1,2]", "MINUS[1,4]", "INT(0)[1,5]", "MINUS[1,7]",
    "INT(32767)[1,8]"))
t("INT14_Negative_32768", "-32768\n", ERR)
t("INT15_Numbers_Variety", "1 9 10 99 100 1000 10000 32766 20000 30000\n")
t("INT16_Decimal_Points", "3.14 .5 5.\n",
  E("INT(3)[1,1]", "DOT[1,2]", "INT(14)[1,3]", "DOT[1,6]", "INT(5)[1,7]",
    "INT(5)[1,9]", "DOT[1,10]"))
t("INT17_Zero_Next_To_Punct", "0;0)0+0\n",
  E("INT(0)[1,1]", "SEMICOLON[1,2]", "INT(0)[1,3]", "RPAREN[1,4]", "INT(0)[1,5]",
    "PLUS[1,6]", "INT(0)[1,7]"))
t("INT18_Out_Of_Range_After_Valid", "int x := 5;\nint y := 40000;\n", ERR)
t("INT19_Leading_Zero_Last_Line", "int x := 1;\nint y := 2;\nint z := 08;\n", ERR)
t("INT20_Zero_Space_ID", "0 x\n", E("INT(0)[1,1]", "ID(x)[1,3]"))
t("INT21_Leading_Zero_Zero_Point", "00.5\n", ERR)
t("INT22_Max_In_Expression", "x := 32767 - 1 + 0;\n")
t("INT23_Leading_Zeros_Long", "0000000000\n", ERR)
t("INT24_Out_Of_Range_100000", "100000\n", ERR)

# =====================================================================
# STR: strings
# =====================================================================
t("STR01_Simple", '"Dan"', 'STRING("Dan")[1,1]')
t("STR02_Empty", '""', 'STRING("")[1,1]')
t("STR03_Mixed_Case", '"HelloWorld" "abcXYZ"\n',
  E('STRING("HelloWorld")[1,1]', 'STRING("abcXYZ")[1,14]'))
t("STR04_Space_Inside", '"a b"\n', ERR)
t("STR05_Digit_Inside", '"a1"\n', ERR)
t("STR06_Comma_Inside", '"a,b"\n', ERR)
t("STR07_Unclosed_EOF", '"abc', ERR)
t("STR08_Unclosed_Newline", '"abc\n"\n', ERR)
t("STR09_Lone_Quote", '"', ERR)
t("STR10_Escaped_Quote", '"a\\"b"\n', ERR)
t("STR11_Adjacent_Strings", '"ab""cd"\n', E('STRING("ab")[1,1]', 'STRING("cd")[1,5]'))
t("STR12_String_Then_ID", '"abc"def\n', E('STRING("abc")[1,1]', "ID(def)[1,6]"))
t("STR13_ID_Then_String", 'abc"def"\n', E("ID(abc)[1,1]", 'STRING("def")[1,4]'))
t("STR14_Keyword_In_String", '"if" "class"\n', E('STRING("if")[1,1]', 'STRING("class")[1,6]'))
t("STR15_Four_Quotes", '""""\n', E('STRING("")[1,1]', 'STRING("")[1,3]'))
t("STR16_Three_Quotes", '"""\n', ERR)
t("STR17_String_In_Program", 'string s := "Hello";\nPrintString(s);\n',
  E("TYPE_STRING[1,1]", "ID(s)[1,8]", "ASSIGN[1,10]", 'STRING("Hello")[1,13]',
    "SEMICOLON[1,20]", "ID(PrintString)[2,1]", "LPAREN[2,12]", "ID(s)[2,13]",
    "RPAREN[2,14]", "SEMICOLON[2,15]"))
t("STR18_Underscore_Inside", '"a_b"\n', ERR)
t("STR19_Hebrew_Inside", '"\u05e9\u05dc\u05d5\u05dd"\n', ERR)
t("STR20_Unclosed_At_End_Of_Program", 'int x := 1;\nstring s := "oops;\n', ERR)
t("STR21_Long_String", '"' + "abcXYZ" * 100 + '"\n', 'STRING("' + "abcXYZ" * 100 + '")[1,1]')
t("STR22_Slashes_Inside", '"a//b"\n', ERR)
t("STR23_Tab_Inside", '"a\tb"\n', ERR)
t("STR24_Comment_Inside", '"/*x*/"\n', ERR)
t("STR25_Position_After_String", '"abc" x\n"" y\n',
  E('STRING("abc")[1,1]', "ID(x)[1,7]", 'STRING("")[2,1]', "ID(y)[2,4]"))
t("STR26_Dot_Inside", '"a.b"\n', ERR)

# =====================================================================
# C1: Type-1 comments  //
# =====================================================================
t("C1_01_Simple", "// hello world\nx", "ID(x)[2,1]")
t("C1_02_Empty_Comment", "//\nx", "ID(x)[2,1]")
t("C1_03_All_Allowed_Chars",
  "// abcXYZ 0123456789 ( ) [ ] { } ? ! + - * / . ;\t\nx", "ID(x)[2,1]")
t("C1_04_After_Code", "x := 1; // set x\ny := 2;\n",
  E("ID(x)[1,1]", "ASSIGN[1,3]", "INT(1)[1,6]", "SEMICOLON[1,7]",
    "ID(y)[2,1]", "ASSIGN[2,3]", "INT(2)[2,6]", "SEMICOLON[2,7]"))
t("C1_05_Contains_Block_Start", "// /* not a block\nx\n", "ID(x)[2,1]")
t("C1_06_Contains_Block_End", "// */\nx\n", "ID(x)[2,1]")
t("C1_07_Triple_Slash", "/// hi\nx\n", "ID(x)[2,1]")
t("C1_08_Consecutive_Comments", "// a\n// b\n//c\nx\n", "ID(x)[4,1]")
t("C1_09_Line_Numbers_After", "a\n// c\nb\n// d\n\nc\n",
  E("ID(a)[1,1]", "ID(b)[3,1]", "ID(c)[6,1]"))
t("C1_10_No_Space_Before", "x//c\ny", E("ID(x)[1,1]", "ID(y)[2,1]"))
t("C1_11_Inside_Expression", "a +// c\nb\n", E("ID(a)[1,1]", "PLUS[1,3]", "ID(b)[2,1]"))
t("C1_12_Comment_Only_File", "// only a comment\n", "")
t("C1_13_Commented_Assign_Is_Error", "void main()\n{\n    // x := 5;\n}\n", ERR)
t("C1_14_Commented_Call_Is_OK", "// PrintInt(x+1);\nx\n", "ID(x)[2,1]")
t("C1_15_Bad_Char_After_Valid_Lines", "int x := 1;\nint y := 2;\n// what: now\n", ERR)
t("C1_16_Question_Exclamation", "// really?! yes!!!\nx\n", "ID(x)[2,1]")
t("C1_17_Comment_With_Tabs", "//\ta\tb\t\nx\n", "ID(x)[2,1]")
t("C1_18_Comment_Bang_Equals_Error", "// a != b\nx\n", ERR)
t("C1_19_Comment_Then_Blank_Lines", "// c\n\n\n   x\n", "ID(x)[4,4]")
for nm, ch in BAD_EVERYWHERE.items():
    t(f"C1_BAD_{nm}", f"x := 1; // bad{ch}char\ny\n", ERR)

# =====================================================================
# C2: Type-2 comments  /* */
# =====================================================================
t("C2_01_Simple", "/* hello */x", "ID(x)[1,12]")
t("C2_02_Empty", "/**/x", "ID(x)[1,5]")
t("C2_03_Three_Stars", "/***/x", "ID(x)[1,6]")
t("C2_04_Many_Stars", "/******/x", "ID(x)[1,9]")
t("C2_05_Slash_Inside", "/*/ */x", "ID(x)[1,7]")
t("C2_06_Multiline", "/* line1\nline2\n   line3 */ x", "ID(x)[3,13]")
t("C2_07_All_Allowed_Chars",
  "/* abcXYZ 0123456789 ( ) [ ] { } ? ! + - * / . ;\t\n */x", "ID(x)[2,4]")
t("C2_08_Unclosed", "/* abc", ERR)
t("C2_09_Unclosed_Star", "/* abc *", ERR)
t("C2_10_Only_Open", "/*", ERR)
t("C2_11_Open_Then_Slash", "/*/", ERR)
t("C2_12_Unclosed_After_Code", "int x := 1;\n/* never closed\n", ERR)
t("C2_13_Not_Nested", "/* a /* b */ c */",
  E("ID(c)[1,14]", "TIMES[1,16]", "DIVIDE[1,17]"))
t("C2_14_Close_Without_Open", "a*/", E("ID(a)[1,1]", "TIMES[1,2]", "DIVIDE[1,3]"))
t("C2_15_Contains_Line_Comment", "/* // inside */x", "ID(x)[1,16]")
t("C2_16_Between_Tokens", "x/**/y", E("ID(x)[1,1]", "ID(y)[1,6]"))
t("C2_17_Bad_Char_On_Later_Line", "/* ok\nok\nbad, */\nx\n", ERR)
t("C2_18_Long_Multiline",
  "x\n/*\n" + "line of comment text\n" * 10 + "*/ y\n", E("ID(x)[1,1]", "ID(y)[13,4]"))
t("C2_19_Two_Comments", "/* a */ x /* b */ y\n", E("ID(x)[1,9]", "ID(y)[1,19]"))
t("C2_20_Comment_Only_File", "/* only */\n", "")
t("C2_21_Star_Space_Slash_Not_End", "/* a * / b */x", "ID(x)[1,14]")
t("C2_22_Divide_Space_Times", "a / *b\n",
  E("ID(a)[1,1]", "DIVIDE[1,3]", "TIMES[1,5]", "ID(b)[1,6]"))
t("C2_23_Comment_At_EOF", "x /* c */", "ID(x)[1,1]")
t("C2_24_Commented_Assign_Is_Error", "/* x := 3; */\n", ERR)
t("C2_25_Close_Then_Close", "/* a */ */\n", E("TIMES[1,9]", "DIVIDE[1,10]"))
t("C2_26_Stars_Before_Close", "/* a **/x", "ID(x)[1,9]")
t("C2_27_Unclosed_Long", "x\n/*" + " abc\n" * 50, ERR)
t("C2_28_Inside_Expression", "a/*c*/+/*d*/b\n", E("ID(a)[1,1]", "PLUS[1,7]", "ID(b)[1,13]"))
t("C2_29_Columns_After_Multiline", "/*\n*/x y\n", E("ID(x)[2,3]", "ID(y)[2,5]"))
t("C2_30_Empty_Lines_Inside", "/*\n\n\n*/\nx\n", "ID(x)[5,1]")
for nm, ch in BAD_EVERYWHERE.items():
    t(f"C2_BAD_{nm}", f"x := 1; /* bad{ch}char */ y\n", ERR)

# =====================================================================
# OP: operators and punctuation
# =====================================================================
t("OP01_All_Single", "+ - * / = < > ( ) [ ] { } , . ;\n",
  E("PLUS[1,1]", "MINUS[1,3]", "TIMES[1,5]", "DIVIDE[1,7]", "EQ[1,9]", "LT[1,11]",
    "GT[1,13]", "LPAREN[1,15]", "RPAREN[1,17]", "LBRACK[1,19]", "RBRACK[1,21]",
    "LBRACE[1,23]", "RBRACE[1,25]", "COMMA[1,27]", "DOT[1,29]", "SEMICOLON[1,31]"))
t("OP02_All_No_Spaces", "+-*=<>()[]{},.;:=\n",
  E("PLUS[1,1]", "MINUS[1,2]", "TIMES[1,3]", "EQ[1,4]", "LT[1,5]", "GT[1,6]",
    "LPAREN[1,7]", "RPAREN[1,8]", "LBRACK[1,9]", "RBRACK[1,10]", "LBRACE[1,11]",
    "RBRACE[1,12]", "COMMA[1,13]", "DOT[1,14]", "SEMICOLON[1,15]", "ASSIGN[1,16]"))
t("OP03_Assign_No_Spaces", "x:=y\n", E("ID(x)[1,1]", "ASSIGN[1,2]", "ID(y)[1,4]"))
t("OP04_Colon_Alone", ":\n", ERR)
t("OP05_Colon_Space_Equals", "x : = 1;\n", ERR)
t("OP06_Assign_Then_Eq", ":==\n", E("ASSIGN[1,1]", "EQ[1,3]"))
t("OP07_Eq_Then_Colon", "=:\n", ERR)
t("OP08_Double_Eq", "==\n", E("EQ[1,1]", "EQ[1,2]"))
t("OP09_LE_GE_Are_Two_Tokens", "<= >=\n", E("LT[1,1]", "EQ[1,2]", "GT[1,4]", "EQ[1,5]"))
t("OP10_Not_Equal_Is_Error", "a != b\n", ERR)
t("OP11_LT_GT", "<>\n", E("LT[1,1]", "GT[1,2]"))
t("OP12_Divide_Chain", "a / b / c\n",
  E("ID(a)[1,1]", "DIVIDE[1,3]", "ID(b)[1,5]", "DIVIDE[1,7]", "ID(c)[1,9]"))
t("OP13_Expression", "(a+b)*(c-d)/e\n",
  E("LPAREN[1,1]", "ID(a)[1,2]", "PLUS[1,3]", "ID(b)[1,4]", "RPAREN[1,5]",
    "TIMES[1,6]", "LPAREN[1,7]", "ID(c)[1,8]", "MINUS[1,9]", "ID(d)[1,10]",
    "RPAREN[1,11]", "DIVIDE[1,12]", "ID(e)[1,13]"))
t("OP14_Array_Access", "arr[i+1] := arr[i]*2;\n")
t("OP15_Field_Access", "a.b.c := d.e;\n")
t("OP16_Minus_Minus", "a--b\n", E("ID(a)[1,1]", "MINUS[1,2]", "MINUS[1,3]", "ID(b)[1,4]"))
t("OP17_Five_Pluses", "x+++++y\n",
  E("ID(x)[1,1]", "PLUS[1,2]", "PLUS[1,3]", "PLUS[1,4]", "PLUS[1,5]", "PLUS[1,6]",
    "ID(y)[1,7]"))
t("OP18_Double_Assign", ":=:=\n", E("ASSIGN[1,1]", "ASSIGN[1,3]"))
t("OP19_Assign_Newline_Split", "x :\n= 1;\n", ERR)
for nm, ch in {"Bang": "!", "Question": "?", "Amp": "&", "Pipe": "|", "Percent": "%",
               "Caret": "^", "Tilde": "~", "Backtick": "`", "At": "@", "Hash": "#",
               "Dollar": "$", "Backslash": "\\", "SQuote": "'", "Underscore": "_"}.items():
    t(f"OP_BAD_{nm}", f"x := a {ch} b;\n", ERR)
t("OP20_Logical_And_C_Style", "a && b\n", ERR)
t("OP21_Logical_Or_C_Style", "a || b\n", ERR)

# =====================================================================
# WS: whitespace, line/column positions
# =====================================================================
t("WS01_Empty_File", "", "")
t("WS02_Only_Whitespace", "   \n\t\n  ", "")
t("WS03_Only_Newlines", "\n\n\n", "")
t("WS04_Leading_Spaces", "     x", "ID(x)[1,6]")
t("WS05_Tab_Counts_As_One_Column", "\tx\t\ty", E("ID(x)[1,2]", "ID(y)[1,5]"))
t("WS06_Blank_Lines", "\n\n\nx\n\n y", E("ID(x)[4,1]", "ID(y)[6,2]"))
t("WS07_No_Trailing_Newline", "x", "ID(x)[1,1]")
t("WS08_Trailing_Spaces", "x   \n   ", "ID(x)[1,1]")
t("WS09_Long_Line", " ".join(f"v{k}" for k in range(300)) + "\n")
t("WS10_Many_Lines", "".join(f"v{k}\n" for k in range(1, 1001)))
t("WS11_Mixed_Whitespace", " \t \n\t x \t\n", "ID(x)[2,3]")
t("WS12_Token_Per_Line", "a\nb\nc", E("ID(a)[1,1]", "ID(b)[2,1]", "ID(c)[3,1]"))
t("WS13_Indented_Block", "{\n    x;\n        y;\n}\n",
  E("LBRACE[1,1]", "ID(x)[2,5]", "SEMICOLON[2,6]", "ID(y)[3,9]", "SEMICOLON[3,10]",
    "RBRACE[4,1]"))
t("WS14_Column_100", " " * 99 + "x\n", "ID(x)[1,100]")

# =====================================================================
# ERR: where the error is (whole output must be just ERROR)
# =====================================================================
VALID_PROG = ("int IsPrime(int p)\n{\n    int i := 2;\n    while (i < p)\n    {\n"
              "        i := i + 1;\n    }\n    return 1;\n}\n")
t("ERR01_Error_First_Char", "$x := 5;\n", ERR)
t("ERR02_Error_Middle", "x := 5;\ny := @;\nz := 6;\n", ERR)
t("ERR03_Error_Last_Char", "x := 5;$", ERR)
t("ERR04_Error_After_Many_Tokens", VALID_PROG * 20 + "#\n", ERR)
t("ERR05_Error_Last_Line_No_Newline", VALID_PROG + "@", ERR)
t("ERR06_Hebrew_In_Code", "x := \u05e9\u05dc\u05d5\u05dd;\n", ERR)
t("ERR07_Emoji", "x := 1; \U0001F600\n", ERR)
t("ERR08_Null_Byte", "x\0y\n", ERR)
t("ERR09_Backslash_Only", "\\", ERR)
t("ERR10_Tilde_Only", "~", ERR)
t("ERR11_Error_After_Comment", "/* fine */ x := 1; ?\n", ERR)
t("ERR12_Two_Errors", "$ x @\n", ERR)
t("ERR13_Bad_String_Mid_Program", VALID_PROG + 'string s := "bad string";\n' + VALID_PROG, ERR)
t("ERR14_Bad_Int_Mid_Program", VALID_PROG + "x := 99999;\n" + VALID_PROG, ERR)
t("ERR15_Unicode_Letter_ID", "caf\u00e9 := 1;\n", ERR)
t("ERR16_Nonbreaking_Space", "x\u00a0:= 1;\n", ERR)

# =====================================================================
# PRG: realistic L programs
# =====================================================================
t("PRG01_Classes_Inheritance", """/* Classes and inheritance */
class Father
{
    int i;
    int j;
    void foo(int x) { i := x; }
}
class Son extends Father
{
    int k;
    string name := "Son";
}
void main()
{
    Son s := new Son;
    s.foo(7);
    s.k := s.i + s.j;
}
""")
t("PRG02_Arrays", """array IntArray = int[]
array Matrix = IntArray[]

void main()
{
    IntArray arr := new int[10];
    Matrix m := new IntArray[3];
    int i := 0;
    while (i < 10)
    {
        arr[i] := i * i;
        i := i + 1;
    }
    m[0] := arr;
    PrintInt(m[0][9]);
}
""")
t("PRG03_Strings", """string greeting := "Hello";
string empty := "";
void main()
{
    string s := greeting;
    if (s = "Hello")
    {
        PrintString("Yes");
    }
    else
    {
        PrintString("No");
    }
    string t := "abc""def";
}
""")
t("PRG04_Nested_Control", """int f(int a, int b)
{
    if (a < b and b < 100)
    {
        while (a < b or a = 0)
        {
            if (a > 50)
            {
                return a;
            }
            a := a + 1;
        }
    }
    else
    {
        return -1;
    }
    return 0;
}
""")
t("PRG05_Every_Token_Kind", """array A = int[]
class B extends C { int x; string s; }
void f(int p, int q) { }
void main()
{
    A a := new int[5];
    B b := nil;
    if (a[0] = 1 and 2 < 3 or 4 > 5)
    {
        b.x := (1 + 2) * 3 - 4 / 2;
    }
    else
    {
        while (b.x < 10) { b.x := b.x + 1; }
    }
    b.s := "Done";
    return;
}
""")
t("PRG06_Comments_Everywhere", """/* header comment
   spans lines (with parens) and stuff! */
int /* inline */ x /**/ := /* a */ 5; // trailing comment
// full line comment
void main(/* no params */)
{
    x := x /* times */ * 2; // double it
    /* multi
       line
       inside a function */
}
""")
t("PRG07_Linked_List", """class Node
{
    int value;
    Node next;
}
int Length(Node n)
{
    int len := 0;
    while (n)
    {
        len := len + 1;
        n := n.next;
    }
    return len;
}
void main()
{
    Node a := new Node;
    Node b := new Node;
    a.value := 1;
    b.value := 2;
    a.next := b;
    b.next := nil;
    PrintInt(Length(a));
}
""")
t("PRG08_Bubble_Sort", """array IntArray = int[]

void Sort(IntArray arr, int n)
{
    int i := 0;
    while (i < n)
    {
        int j := 0;
        while (j < n - i - 1)
        {
            if (arr[j+1] < arr[j])
            {
                int tmp := arr[j];
                arr[j] := arr[j+1];
                arr[j+1] := tmp;
            }
            j := j + 1;
        }
        i := i + 1;
    }
}
""")
t("PRG09_Fibonacci", """int Fib(int n)
{
    if (n < 2) { return n; }
    return Fib(n-1) + Fib(n-2);
}
void main(void)
{
    int i := 0;
    while (i < 20)
    {
        PrintInt(Fib(i));
        i := i + 1;
    }
}
""")
t("PRG10_Dense_No_Spaces",
  "int f(int a,int b){return a*b+(a-b)/2;}class X extends Y{int z;}"
  "void main(){X x:=new X;x.z:=f(3,4);}\n")
t("PRG11_Boundary_Values", "int a := 0;\nint b := 32767;\nint c := -32767;\nint d := 1;\n")
t("PRG12_String_With_Space_At_End",
  'void main()\n{\n    PrintInt(1);\n    PrintString("Hello World");\n}\n', ERR)
t("PRG13_Method_Calls_Chain", "a.b(c).d(e, f.g).h := i.j();\n")
t("PRG14_Class_With_Methods", """class Point extends Shape
{
    int x;
    int y;
    int Dist(Point other)
    {
        int dx := x - other.x;
        int dy := y - other.y;
        return dx * dx + dy * dy;
    }
    void Move(int ddx, int ddy)
    {
        x := x + ddx;
        y := y + ddy;
    }
}
""")
t("PRG15_Self_Check_Style_With_Comment", """int Max(int a, int b)
{
    if (a > b)
    {
        // a is bigger ...
        return a;
    }
    /****************************/
    /* otherwise b is the max!! */
    /****************************/
    return b;
}
""")

# =====================================================================
# RND: random token soups (seeded, reproducible)
# =====================================================================
KW_LIST = ["array", "class", "extends", "new", "nil", "if", "else", "while",
           "return", "int", "string", "void", "and", "or"]
OPS = ["+", "-", "*", "/", "=", "<", ">", "(", ")", "[", "]", "{", "}", ",", ".", ";", ":="]
LET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIG = "0123456789"
CMT_CHARS = LET + DIG + " \t()[]{}?!+-*/.;"


def rnd_lexeme(r):
    k = r.random()
    if k < 0.15:
        return r.choice(KW_LIST)
    if k < 0.40:
        return r.choice(LET) + "".join(r.choice(LET + DIG) for _ in range(r.randint(0, 6)))
    if k < 0.55:
        return str(r.choice([0, 1, 7, 42, 100, 32767, r.randint(0, 32767)]))
    if k < 0.65:
        return '"' + "".join(r.choice(LET) for _ in range(r.randint(0, 6))) + '"'
    return r.choice(OPS)


def rnd_comment_body(r, allow_newline):
    chars = CMT_CHARS + ("\n" if allow_newline else "")
    body = "".join(r.choice(chars) for _ in range(r.randint(0, 25)))
    while "*/" in body:
        body = body.replace("*/", "* /")
    return body


def rnd_sep(r):
    k = r.random()
    if k < 0.30:
        return ""
    if k < 0.65:
        return " "
    if k < 0.75:
        return "\n" + " " * r.randint(0, 6)
    if k < 0.82:
        return "\t"
    if k < 0.92:
        return " /*" + rnd_comment_body(r, True) + "*/ "
    return " //" + rnd_comment_body(r, False) + "\n"


def unsafe(a, b):
    if not a or not b:
        return False
    x, y = a[-1], b[0]
    if x.isalnum() and y.isalnum():
        return True
    if x == "/" and y in "/*":
        return True
    return False


def rnd_program(seed, n):
    r = random.Random(seed)
    out = ""
    for _ in range(n):
        lx = rnd_lexeme(r)
        sep = rnd_sep(r)
        piece = sep + lx
        if unsafe(out, piece):
            piece = " " + piece
        out += piece
    return out + "\n"


for k in range(1, 26):
    text = rnd_program(1000 + k, 40 + 8 * k)
    assert render(text) != ERR, f"random program {k} unexpectedly invalid"
    t(f"RND{k:02d}_Random_Valid", text)

for k in range(1, 11):
    r = random.Random(5000 + k)
    base = rnd_program(5000 + k, 150)
    pos = r.randint(0, len(base))
    bad = r.choice(["$", "@", "#", "_", "~", "`", "\\", "'", "%", "&", "|", "^"])
    t(f"RNDERR{k:02d}_Random_With_Illegal_Char", base[:pos] + bad + base[pos:], ERR)

# =====================================================================
# STRESS: big inputs (self-check gives every test 10 seconds)
# =====================================================================
BIG_BLOCK = MAIN[[n for n, _, _ in MAIN].index("PRG05_Every_Token_Kind")][1]
t("STRESS01_Big_Program_10k_Lines", BIG_BLOCK * 550)
t("STRESS02_Big_Program_Error_At_End", BIG_BLOCK * 550 + "$\n", ERR)
t("STRESS03_Huge_Block_Comment", "/*" + ("abc def 123 ()[]{}?!+-/.;*\n" * 8000) + "*/ x\n",
  "ID(x)[8001,4]")
t("STRESS04_50k_Blank_Lines", "\n" * 50000 + "x\n", "ID(x)[50001,1]")
t("STRESS05_Huge_Line_Comment", "//" + "a" * 300000 + "\nx\n", "ID(x)[2,1]")


# ===========================================================================
# Write the files
# ===========================================================================
def main():
    tdir = os.path.join(OUT_DIR, "tests")
    edir = os.path.join(OUT_DIR, "expected_output")
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)          # always start from a clean folder
    os.makedirs(tdir)
    os.makedirs(edir)
    for name, text, hand in MAIN:
        ref = render(text)
        if hand is not None and hand != ref:
            sys.exit(f"TEST_{name}: hand-written expectation != reference lexer")
        with open(os.path.join(tdir, f"TEST_{name}.txt"), "w",
                  encoding="utf-8", newline="") as f:
            f.write(text)
        with open(os.path.join(edir, f"TEST_{name}_Expected_Output.txt"), "w",
                  newline="") as f:
            f.write(hand if hand is not None else ref)
    print(f"Wrote {len(MAIN)} tests to {OUT_DIR}")


if __name__ == "__main__":
    main()