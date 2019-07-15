package com.test;

public class TestArgumentAnnotations {
	public static void main(String[] args) {
		assert operate(5, "add", 2) == 5 + 2;
		assert operate(2, "to the power of", 3) == 8;
	}
	
	static int operate(int x, String op, int y) {
		return switch(op) {
			case "add" -> x + y;
			case "subtract" -> x - y;
			case "multiply" -> x * y;
			case "divide" -> x / y;
			case "modulo", "modulus" -> x % y;
			case "pow", "exponentiate", "power", "to the power of", "to the" -> (int)Math.pow(x, y);
			case "difference" -> Math.abs(x - y);
			default -> throw new IllegalArgumentException();
		};
	}
}