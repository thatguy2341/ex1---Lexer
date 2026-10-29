/***************************/
/* FILE NAME: LEX_FILE.lex */
/***************************/

/*************/
/* USER CODE */
/*************/

import java_cup.runtime.*;

/******************************/
/* DOLLAR DOLLAR - DON'T TOUCH! */
/******************************/

%%

/************************************/
/* OPTIONS AND DECLARATIONS SECTION */
/************************************/
   
/*****************************************************/ 
/* Lexer is the name of the class JFlex will create. */
/* The code will be written to the file Lexer.java.  */
/*****************************************************/ 
%class Lexer

/********************************************************************/
/* The current line number can be accessed with the variable yyline */
/* and the current column number with the variable yycolumn.        */
/********************************************************************/
%line
%column

/*******************************************************************************/
/* Note that this has to be the EXACT same name of the class the CUP generates */
/*******************************************************************************/
%cupsym TokenNames

/******************************************************************/
/* CUP compatibility mode interfaces with a CUP generated parser. */
/******************************************************************/
%cup

/****************/
/* DECLARATIONS */
/****************/
/*****************************************************************************/   
/* Code between %{ and %}, both of which must be at the beginning of a line, */
/* will be copied verbatim (letter to letter) into the Lexer class code.     */
/* Here you declare member variables and functions that are used inside the  */
/* scanner actions.                                                          */  
/*****************************************************************************/   
%{
	/*********************************************************************************/
	/* Create a new java_cup.runtime.Symbol with information about the current token */
	/*********************************************************************************/
	private Symbol symbol(int type)               {return new Symbol(type, yyline, yycolumn);}
	private Symbol symbol(int type, Object value) {return new Symbol(type, yyline, yycolumn, value);}

	/*******************************************/
	/* Enable line number extraction from main */
	/*******************************************/
	public int getLine() { return yyline + 1; } 

	/**********************************************/
	/* Enable token position extraction from main */
	/**********************************************/
	public int getTokenStartPosition() { return yycolumn + 1; } 
%}

/***********************/
/* MACRO DECLARATIONS */
/***********************/
LineTerminator	= \r|\n|\r\n
WhiteSpace		= {LineTerminator} | [ \t]
INTEGER			= 0 | [1-9][0-9]*
ID				= [a-zA-Z][a-zA-Z0-9]*
STRING			= \"[a-zA-Z]*\"
ARRAY 			= "array"
CLASS 			= "class"
EXTENDS 		= "extends"
NEW 			= "new"
NIL 			= "nil"
IF 				= "if"
ELSE 			= "else"
WHILE 			= "while"
RETURN 			= "return"
TYPE_INT 		= "int"
TYPE_STRING 	= "string"
TYPE_VOID 		= "void"
PLUS 			= "+"
MINUS			= "-"
TIMES			= "*"
DIVIDE			= "/"
EQ 				= "="
LT 				= "<"
GT 				= ">"
AND 			= "and"
OR 				= "or"
LPAREN 			= "("
RPAREN 			= ")"
LBRACK 			= "["
RBRACK 			= "]"
LBRACE 			= "{"
RBRACE 			= "}"
COMMA 			= ","
DOT 			= "."
SEMICOLON 		= ";"
ASSIGN 			= ":="
COMMENT_ROW 	= "//"
COMMENT_BLOCK_BEGIN	= "/*"
COMMENT_BLOCK_END	= "*/"
COMMENT_CHAR 		= [a-zA-Z0-9\(\)\[\]\{\}\?\!\+\-\*\/\.\;] | {WhiteSpace}

%state COMMENT_BLOCK
%state COMMENT_ROW


/******************************/
/* DOLLAR DOLLAR - DON'T TOUCH! */
/******************************/

%%

/************************************************************/
/* LEXER matches regular expressions to actions (Java code) */
/************************************************************/

/**************************************************************/
/* YYINITIAL is the state at which the lexer begins scanning. */
/* So these regular expressions will only be matched if the   */
/* scanner is in the start state YYINITIAL.                   */
/**************************************************************/

<YYINITIAL> {
{ARRAY}         { return symbol(TokenNames.ARRAY); }
{CLASS}         { return symbol(TokenNames.CLASS); }
{EXTENDS}       { return symbol(TokenNames.EXTENDS); }
{NEW}           { return symbol(TokenNames.NEW); }
{NIL}           { return symbol(TokenNames.NIL); }
{IF}            { return symbol(TokenNames.IF); }
{ELSE}          { return symbol(TokenNames.ELSE); }
{WHILE}         { return symbol(TokenNames.WHILE); }
{RETURN}        { return symbol(TokenNames.RETURN); }
{TYPE_INT}      { return symbol(TokenNames.TYPE_INT); }
{TYPE_STRING}   { return symbol(TokenNames.TYPE_STRING); }
{TYPE_VOID}     { return symbol(TokenNames.TYPE_VOID); }
{AND}           { return symbol(TokenNames.AND); }
{OR}            { return symbol(TokenNames.OR); }

{PLUS}          { return symbol(TokenNames.PLUS); }
{MINUS}         { return symbol(TokenNames.MINUS); }
{TIMES}         { return symbol(TokenNames.TIMES); }
{DIVIDE}        { return symbol(TokenNames.DIVIDE); }
{LPAREN}        { return symbol(TokenNames.LPAREN); }
{RPAREN}        { return symbol(TokenNames.RPAREN); }
{LBRACK}        { return symbol(TokenNames.LBRACK); }
{RBRACK}        { return symbol(TokenNames.RBRACK); }
{LBRACE}        { return symbol(TokenNames.LBRACE); }
{RBRACE}        { return symbol(TokenNames.RBRACE); }
{COMMA}         { return symbol(TokenNames.COMMA); }
{DOT}           { return symbol(TokenNames.DOT); }
{SEMICOLON}     { return symbol(TokenNames.SEMICOLON); }
{ASSIGN}        { return symbol(TokenNames.ASSIGN); }
{EQ}            { return symbol(TokenNames.EQ); }
{LT}            { return symbol(TokenNames.LT); }
{GT}            { return symbol(TokenNames.GT); }


{STRING} 			{ return symbol(TokenNames.STRING, yytext()); }
{INTEGER}			{
	int annoying_num_of_tal = Integer.valueOf(yytext()); 
	if(annoying_num_of_tal > 32767 || annoying_num_of_tal < 0) throw new Error();
 	return symbol(TokenNames.NUMBER, annoying_num_of_tal);
}

{ID}				{ return symbol(TokenNames.ID,     yytext());}
{WhiteSpace}		{ /* just skip what was found, do nothing */ }

{COMMENT_BLOCK_BEGIN} { yybegin(COMMENT_BLOCK);} 
{COMMENT_ROW} 		{ yybegin(COMMENT_ROW); }

<<EOF>>				{ return symbol(TokenNames.EOF);}

[^] 				{ throw new Error(); }
}





<COMMENT_BLOCK>{

{COMMENT_BLOCK_END} { yybegin(YYINITIAL);}
{COMMENT_CHAR} 		{}
<<EOF>>				{ throw new Error();}
[^] 				{ throw new Error(); }
}




<COMMENT_ROW>{

{LineTerminator}	{ yybegin(YYINITIAL);}
{COMMENT_CHAR} 		{}
<<EOF>> 			{ yybegin(YYINITIAL); return symbol(TokenNames.EOF); }
[^] 				{ throw new Error(); }
}