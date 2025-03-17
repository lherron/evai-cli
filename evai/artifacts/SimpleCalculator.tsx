import React, { useState } from 'react';

function SimpleCalculator() {
  const [display, setDisplay] = useState('0');
  const [firstOperand, setFirstOperand] = useState(null);
  const [operator, setOperator] = useState(null);
  const [waitingForSecondOperand, setWaitingForSecondOperand] = useState(false);

  const inputDigit = (digit) => {
    if (waitingForSecondOperand) {
      setDisplay(String(digit));
      setWaitingForSecondOperand(false);
    } else {
      setDisplay(display === '0' ? String(digit) : display + digit);
    }
  };

  const inputDecimal = () => {
    if (waitingForSecondOperand) {
      setDisplay('0.');
      setWaitingForSecondOperand(false);
      return;
    }
    
    if (!display.includes('.')) {
      setDisplay(display + '.');
    }
  };

  const clearDisplay = () => {
    setDisplay('0');
    setFirstOperand(null);
    setOperator(null);
    setWaitingForSecondOperand(false);
  };

  const performOperation = (nextOperator) => {
    const inputValue = parseFloat(display);

    if (firstOperand === null) {
      setFirstOperand(inputValue);
    } else if (operator) {
      const result = calculate(firstOperand, inputValue, operator);
      setDisplay(String(result));
      setFirstOperand(result);
    }

    setWaitingForSecondOperand(true);
    setOperator(nextOperator);
  };

  const calculate = (firstOperand, secondOperand, operator) => {
    switch (operator) {
      case '+':
        return firstOperand + secondOperand;
      case '-':
        return firstOperand - secondOperand;
      case '*':
        return firstOperand * secondOperand;
      case '/':
        return firstOperand / secondOperand;
      default:
        return secondOperand;
    }
  };

  const handleEquals = () => {
    if (!operator || firstOperand === null) return;
    
    const inputValue = parseFloat(display);
    const result = calculate(firstOperand, inputValue, operator);
    
    setDisplay(String(result));
    setFirstOperand(null);
    setOperator(null);
    setWaitingForSecondOperand(false);
  };

  return (
    <div className="calculator">
      <div className="calculator-display">{display}</div>
      <div className="calculator-keypad">
        <div className="input-keys">
          <div className="function-keys">
            <button className="key-clear" onClick={clearDisplay}>
              AC
            </button>
          </div>
          <div className="digit-keys">
            <button onClick={() => inputDigit(7)}>7</button>
            <button onClick={() => inputDigit(8)}>8</button>
            <button onClick={() => inputDigit(9)}>9</button>
            <button onClick={() => inputDigit(4)}>4</button>
            <button onClick={() => inputDigit(5)}>5</button>
            <button onClick={() => inputDigit(6)}>6</button>
            <button onClick={() => inputDigit(1)}>1</button>
            <button onClick={() => inputDigit(2)}>2</button>
            <button onClick={() => inputDigit(3)}>3</button>
            <button onClick={() => inputDigit(0)}>0</button>
            <button onClick={inputDecimal}>.</button>
          </div>
        </div>
        <div className="operator-keys">
          <button onClick={() => performOperation('/')}>÷</button>
          <button onClick={() => performOperation('*')}>×</button>
          <button onClick={() => performOperation('-')}>−</button>
          <button onClick={() => performOperation('+')}>+</button>
          <button onClick={handleEquals}>=</button>
        </div>
      </div>
      <style jsx>{`
        .calculator {
          width: 320px;
          margin: 0 auto;
          background-color: #f0f0f0;
          border-radius: 8px;
          box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
          font-family: Arial, sans-serif;
        }
        
        .calculator-display {
          padding: 20px;
          text-align: right;
          background-color: #333;
          color: white;
          font-size: 24px;
          border-top-left-radius: 8px;
          border-top-right-radius: 8px;
          min-height: 30px;
          overflow: hidden;
        }
        
        .calculator-keypad {
          display: flex;
        }
        
        .input-keys {
          flex: 3;
        }
        
        .operator-keys {
          flex: 1;
          background-color: #e0e0e0;
        }
        
        button {
          width: 100%;
          height: 50px;
          border: none;
          background-color: #f9f9f9;
          font-size: 20px;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        
        button:hover {
          background-color: #e9e9e9;
        }
        
        .function-keys button {
          background-color: #ddd;
        }
        
        .operator-keys button {
          background-color: #f5923e;
          color: white;
        }
        
        .operator-keys button:hover {
          background-color: #f7a763;
        }
        
        .digit-keys {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
        }
      `}</style>
    </div>
  );
}

export default SimpleCalculator;