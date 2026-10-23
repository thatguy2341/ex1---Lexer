import java.io.*;

import java_cup.runtime.Symbol;
   
public class Main
{
	static public void main(String argv[])
	{
		Lexer l;
		Symbol s;
		FileReader fileReader;
		PrintWriter fileWriter;
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
				fileWriter.print(l.getLine());
				fileWriter.print(": ");
				fileWriter.print(s.value);
				fileWriter.print("\n");
				
				/***********************/
				/* [8] Read next token */
				/***********************/
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
			     
		catch (Exception e)
		{
			
			e.printStackTrace();
			fileWriter.close();
			fileWriter = new PrintWriter(outputFileName);
			fileWriter.print("ERROR");
			fileWriter.close();
		}
	}
}


/* 
TODO: check if the error actually deletes the whole file and leave only ERROR.
TODO: check if there is only one " then there would error in any case possible and wont find another token instead.
TODO: Actually check if the importance of the rules work.
TODO: Check if there is end of file inside a comma row (i.e. //) then is there supposed to be an ERROR or not.
*/ 
