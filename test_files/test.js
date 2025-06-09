// Test JavaScript file
function greet(name) {
    console.log(`Hello, ${name}!`);
}

class Calculator {
    add(a, b) {
        return a + b;
    }
    
    subtract(a, b) {
        return a - b;
    }
}

module.exports = { greet, Calculator };