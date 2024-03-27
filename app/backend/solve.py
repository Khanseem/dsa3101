from latex2sympy2 import latex2latex, latex2sympy

"""
the 2 inputs it should work on is latex code and string. 
it should be able to check if the solver is applicable
 (e.g., if there is = or >= or <= etc.), then output if there is probably an error or not.
take note that the latex code may not be mathematically right 
e.g. fraction can be frac{}{234} and still be parsed. 
for such instances, the code should determine that it cannot determine if its right or not
"""
import re

import numexpr as ne


def simplify_latex(tex):
    convertedsympy = latex2sympy(tex)
    calculatedlatex = latex2latex(tex)
    # print(calculatedlatex)
    return calculatedlatex


def simplify_str(s):
    # print(f"{s} evaluates to {ne.evaluate(s)} ")
    try:
        return ne.evaluate(s.strip())
    except:
        return "Invalid"


def compare_lhs_rhs(left, right, operator):
    if operator == "<":
        if left < right:
            # print("lhs is less than rhs")
            return True
        else:
            # print("lhs is not less than rhs")
            return False
    elif operator == "<=":
        if left <= right:
            # print("lhs is less than or equal to rhs")
            return True
        else:
            # print("lhs is not less than or equal to rhs")
            return False
    elif operator == "=" or operator == "==":
        if left == right:
            # print("lhs is equal to rhs")
            return True
        else:
            # print("lhs is not equal than rhs")
            return False
    elif operator == ">":
        if left > right:
            # print("lhs is more than rhs")
            return True
        else:
            # print("lhs is not more than rhs")
            return False
    elif operator == ">=":
        if left >= right:
            # print("lhs is more than or equal to rhs")
            return True
        else:
            # print("lhs is not more than or equal to rhs")
            return False
    else:
        return True


def solve_str(solution):
    letters = list(solution)
    operator_lst = ["<=", "==", ">=", "<", ">", "="]
    operators = []
    workings = []
    current_string = []
    try:
        while letters[0] in operator_lst:
            letters = letters[1:]
        while letters[-1] in operator_lst:
            letters = letters[:-1]

        for letter in letters:
            if letter in operator_lst:
                if current_string == []:
                    # if the current string is empty, assume that the previous iteration ran added an operator to operator list
                    operator = operators.pop()
                    operator = "".join([operator, letter])
                    operators.append(operator)
                else:
                    # if the current string is not empty, then we add the string to the strings and reset teh string and add the operator
                    s = "".join(current_string)
                    workings.append(s)
                    current_string = []
                    operators.append(letter)
            else:
                # if the word is not in the operator list, it is a string. add it to current string
                current_string.append(letter)
        s = "".join(current_string)
        workings.append(s)

        # print(operators)
        # print(workings)

        statement_lst = True
        if len(operators) == 0:
            # print('no operators identified')
            return True
        else:
            for i in range(len(operators)):
                rhs = workings[i + 1]
                lhs = workings[i]
                left = simplify_str(lhs)
                right = simplify_str(rhs)
                operator = operators[i]
                # print(rhs, lhs, left, right, operator)
                # print(operator)
                if left == "invalid" or right == "invalid":
                    statement = True
                else:
                    statement = compare_lhs_rhs(left, right, operator)
                # print( f"The working in statement {i} with regard to {lhs} and {rhs} is {statement}." )
                statement_lst= statement_lst and statement
                #print(statement_lst,statement)
        # print(statement_lst[0])
        return statement_lst

    # except Exception as e: print(e)
    except:
        return True


"""
def solve_latex(solution):
    letters = list(solution)
    operator_lst = ['<=', '==', '>=', '<', '>', '=']

    #get all equal signs and check if its encapsulated in brackets

    operators = []
    workings = []
    current_string = []
    while letters[0] in operator_lst:
        letters = letters[1:]
    while letters[-1] in operator_lst:
        letters = letters[:-1]

    left_bracket_lst = ['{', '[', '(']
    right_bracket_lst = ['}', ']', ')']
    left_bracket = []
    current_string = []
    for letter in letters:
        if left_bracket_lst != []:
            if letter in left_bracket_lst:
                left_bracket.append(letter)
            elif letter in right_bracket_lst:

        if left_bracket == []:
            if letter in operator_lst:
                if current_string == []:
                    # if the current string is empty, assume that the previous iteration ran added an operator to operator list
                    operator = operators.pop()
                    operator = ''.join([operator, letter])
                    # print(operator)
                    operators.append(operator)
                else:
                    # if the current string is not empty, then we add the string to the strings and reset teh string and add the operator
                    s = ''.join(current_string)
                    workings.append(s)
                    current_string = []
                    operators.append(letter)
            else:
                # if the word is not in the operator list, it is a string. add it to current string
                current_string.append(letter)
    s = ''.join(current_string)
    workings.append(s)

    print(operators)
    print(workings)

    statement_lst = []
    if len(operators) == 0:
        print('no operators identified')
    else:
        for i in range(len(operators)):
            rhs = workings[i + 1]
            lhs = workings[i]
            left = simplify_latex(lhs)
            right = simplify_latex(rhs)
            operator = operators[i]
            print(operator)
            statement = compare_lhs_rhs(left, right, operator)
            s = f"The working in statement {i} with regard to {lhs} and {rhs} is {statement}."
            statement_lst.append(s)
    print(statement_lst)

"""


# str_solution = "p ( A ) = 0.3 + 0.2 = 0.7"
# print(solve_str(str_solution))
# except ZeroDivisionError as err:
#     print('Handling run-time error:', err)


# outdated
# example of how it works
# lhs = r"\frac{d}{dn} (n^{3}/6+0.25n^{2})"
# rhs = r"\sum_{i = 1}^{n} i"
# 0.5 (n2 +n )
# compare_lhs_rhs(lhs,rhs)
