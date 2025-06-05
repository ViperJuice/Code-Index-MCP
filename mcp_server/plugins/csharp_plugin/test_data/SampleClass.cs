using System;
using System.ComponentModel.DataAnnotations;
using System.Collections.Generic;
using Microsoft.AspNetCore.Mvc;

namespace SampleWebApi.Models
{
    /// <summary>
    /// Represents a user in the system
    /// </summary>
    public class User
    {
        /// <summary>
        /// Gets or sets the user ID
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// Gets or sets the user name
        /// </summary>
        [Required]
        [StringLength(100)]
        public string Name { get; set; }

        /// <summary>
        /// Gets or sets the user email
        /// </summary>
        [EmailAddress]
        public string Email { get; set; }

        /// <summary>
        /// Gets or sets the user creation date
        /// </summary>
        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        /// <summary>
        /// Determines if the user is active
        /// </summary>
        public bool IsActive { get; set; } = true;
    }

    /// <summary>
    /// Repository interface for user operations
    /// </summary>
    public interface IUserRepository
    {
        Task<User> GetByIdAsync(int id);
        Task<IEnumerable<User>> GetAllAsync();
        Task<User> CreateAsync(User user);
        Task<User> UpdateAsync(User user);
        Task DeleteAsync(int id);
    }

    /// <summary>
    /// Service class for user business logic
    /// </summary>
    public class UserService : IUserService
    {
        private readonly IUserRepository _repository;
        private readonly ILogger<UserService> _logger;

        /// <summary>
        /// Initializes a new instance of the UserService class
        /// </summary>
        /// <param name="repository">User repository</param>
        /// <param name="logger">Logger instance</param>
        public UserService(IUserRepository repository, ILogger<UserService> logger)
        {
            _repository = repository ?? throw new ArgumentNullException(nameof(repository));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <summary>
        /// Gets a user by ID
        /// </summary>
        /// <param name="id">User ID</param>
        /// <returns>User if found, null otherwise</returns>
        public async Task<User> GetUserAsync(int id)
        {
            _logger.LogInformation("Getting user with ID: {UserId}", id);
            
            if (id <= 0)
            {
                throw new ArgumentException("User ID must be positive", nameof(id));
            }

            return await _repository.GetByIdAsync(id);
        }

        /// <summary>
        /// Creates a new user
        /// </summary>
        /// <param name="user">User to create</param>
        /// <returns>Created user</returns>
        public async Task<User> CreateUserAsync(User user)
        {
            if (user == null)
                throw new ArgumentNullException(nameof(user));

            ValidateUser(user);
            
            _logger.LogInformation("Creating new user: {UserName}", user.Name);
            return await _repository.CreateAsync(user);
        }

        /// <summary>
        /// Validates user data
        /// </summary>
        /// <param name="user">User to validate</param>
        private void ValidateUser(User user)
        {
            if (string.IsNullOrWhiteSpace(user.Name))
                throw new ArgumentException("User name is required", nameof(user));

            if (string.IsNullOrWhiteSpace(user.Email))
                throw new ArgumentException("User email is required", nameof(user));
        }
    }

    /// <summary>
    /// User service interface
    /// </summary>
    public interface IUserService
    {
        Task<User> GetUserAsync(int id);
        Task<User> CreateUserAsync(User user);
    }
}