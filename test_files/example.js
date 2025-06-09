// JavaScript test file
class UserManager {
    constructor() {
        this.users = [];
    }

    addUser(name, email) {
        const user = { id: Date.now(), name, email };
        this.users.push(user);
        return user;
    }

    findUserById(id) {
        return this.users.find(user => user.id === id);
    }
}

function greetUser(name) {
    return `Hello, ${name}!`;
}

export { UserManager, greetUser };