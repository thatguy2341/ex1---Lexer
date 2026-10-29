import java.io.*;

import java_cup.runtime.Symbol;
   
public class Main
{
	private static final String[] TOKEN_NAMES_STR = {
		"EOF", "PLUS", "MINUS", "TIMES", "DIVIDE", "LPAREN", "RPAREN",
		"INT",
		"ID", "EQ", "LT", "GT", "AND", "OR", "LBRACK", "RBRACK",
		"LBRACE", "RBRACE", "COMMA", "DOT", "SEMICOLON", "ASSIGN",
		"ARRAY", "CLASS", "EXTENDS", "NEW", "NIL", "IF", "ELSE",
		"WHILE", "RETURN", "TYPE_INT", "TYPE_STRING", "TYPE_VOID",
		"STRING", "ERROR"
	};

	static public void main(String argv[])
	{
		Lexer l;
		Symbol s;
		FileReader fileReader;
		PrintWriter fileWriter = null;
		String inputFileName = argv[0];
		String outputFileName = argv[1];
		
		try
		{
			/********************************/
			/* [1] Initialize a file reader */
			/********************************/
			fileReader = new FileReader(inputFileName);

			/********************************/
			/* [2] Initialize a file writer */
			/********************************/
			fileWriter = new PrintWriter(outputFileName);
			
			/******************************/
			/* [3] Initialize a new lexer */
			/******************************/
			l = new Lexer(fileReader);

			/***********************/
			/* [4] Read next token */
			/***********************/
			s = l.next_token();

			/********************************/
			/* [5] Main reading tokens loop */
			/********************************/
			while (s.sym != TokenNames.EOF)
			{
				String name = TOKEN_NAMES_STR[s.sym];
				int line = l.getLine();
				int col = l.getTokenStartPosition();

				String lineToPrint;

				/************************/
				/* [6] Print to console */
				/************************/
				System.out.print("[");
				System.out.print(l.getLine());
				System.out.print(",");
				System.out.print(l.getTokenStartPosition());
				System.out.print("]:");
				System.out.print(s.value);
				System.out.print("\n");
				
				/*********************/
				/* [7] Print to file */
				/*********************/
				
				
				// טוקנים להם יש להדפיס גם את הערך שלהם: ID, STRING ו-INT (שמוגדר ב-cup כ-NUMBER)
				if (s.sym == TokenNames.ID || s.sym == TokenNames.NUMBER || s.sym == TokenNames.STRING) {
					lineToPrint = String.format("%s(%s)[%d,%d]", name, s.value.toString(), line, col);
				} else {
					lineToPrint = String.format("%s[%d,%d]", name, line, col);
				}

				fileWriter.println(lineToPrint);
				
				s = l.next_token();
			}
			
			/******************************/
			/* [9] Close lexer input file */
			/******************************/
			l.yyclose();

			/**************************/
			/* [10] Close output file */
			/**************************/
			fileWriter.close();
    	}
			     
		catch (Throwable e)
		{
			
			if (fileWriter != null) {
				fileWriter.close();
			}
			try {
				fileWriter = new PrintWriter(outputFileName);
				fileWriter.print("ERROR");
				fileWriter.close();
			} catch (Exception f_not_found) {
				f_not_found.printStackTrace();
			}
		}
	}
}


/* 
TODO: check if there is only one " then there would be error in any case possible and wont find another token instead.
TODO: Actually check if the importance of the rules work.
TODO: Check if there is end of file inside a comma row (i.e. //) then is there supposed to be an ERROR or not.
*/ 
