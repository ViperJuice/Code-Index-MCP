const express = require('express');
const router = express.Router();

router.post('/api/users', async (req, res) => {
    // Create new user
    const userData = req.body;
    
    // TODO: Add validation
    const user = await User.create(userData);
    
    res.json({ success: true, user });
});

router.get('/api/users/:id', async (req, res) => {
    const userId = req.params.id;
    const user = await User.findById(userId);
    
    if (!user) {
        return res.status(404).json({ error: 'User not found' });
    }
    
    res.json(user);
});
