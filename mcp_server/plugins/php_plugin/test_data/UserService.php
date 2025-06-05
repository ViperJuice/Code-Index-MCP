<?php

namespace App\Services;

use App\Models\User;
use App\Contracts\UserServiceInterface;
use App\Traits\Cacheable;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Mail;
use Illuminate\Support\Str;

/**
 * Service class for user operations
 */
abstract class BaseUserService
{
    protected array $config;
    
    abstract public function process(array $data): bool;
}

/**
 * Concrete implementation of user service
 */
class UserService extends BaseUserService implements UserServiceInterface
{
    use Cacheable;
    
    // Service constants
    public const CACHE_TTL = 3600;
    private const MAX_ATTEMPTS = 3;
    protected const DEFAULT_ROLE = 'user';
    
    /**
     * Configuration array
     */
    protected array $config = [
        'password_length' => 8,
        'require_email_verification' => true,
        'auto_activate' => false,
    ];
    
    /**
     * Static counter for operations
     */
    private static int $operationCount = 0;
    
    /**
     * Constructor
     */
    public function __construct(array $config = [])
    {
        $this->config = array_merge($this->config, $config);
    }
    
    /**
     * Create a new user
     */
    public function createUser(array $userData): User
    {
        $userData['password'] = Hash::make($userData['password']);
        $userData['email_verification_token'] = Str::random(60);
        
        $user = User::create($userData);
        
        if ($this->config['require_email_verification']) {
            $this->sendVerificationEmail($user);
        }
        
        self::$operationCount++;
        
        return $user;
    }
    
    /**
     * Update user information
     */
    public function updateUser(User $user, array $data): bool
    {
        if (isset($data['password'])) {
            $data['password'] = Hash::make($data['password']);
        }
        
        $result = $user->update($data);
        
        if ($result) {
            $this->clearUserCache($user->id);
        }
        
        return $result;
    }
    
    /**
     * Authenticate user
     */
    public function authenticate(string $email, string $password): ?User
    {
        $user = User::where('email', $email)->first();
        
        if (!$user || !Hash::check($password, $user->password)) {
            return null;
        }
        
        $this->updateLastLogin($user);
        
        return $user;
    }
    
    /**
     * Generate password reset token
     */
    public function generatePasswordResetToken(string $email): ?string
    {
        $user = User::where('email', $email)->first();
        
        if (!$user) {
            return null;
        }
        
        $token = Str::random(60);
        $user->update([
            'password_reset_token' => $token,
            'password_reset_expires' => now()->addHours(2),
        ]);
        
        return $token;
    }
    
    /**
     * Reset user password
     */
    public function resetPassword(string $token, string $newPassword): bool
    {
        $user = User::where('password_reset_token', $token)
            ->where('password_reset_expires', '>', now())
            ->first();
            
        if (!$user) {
            return false;
        }
        
        $user->update([
            'password' => Hash::make($newPassword),
            'password_reset_token' => null,
            'password_reset_expires' => null,
        ]);
        
        return true;
    }
    
    /**
     * Get user statistics
     */
    public static function getStatistics(): array
    {
        return [
            'total_users' => User::count(),
            'active_users' => User::active()->count(),
            'operations_count' => self::$operationCount,
        ];
    }
    
    /**
     * Bulk operations on users
     */
    public function bulkUpdate(array $userIds, array $data): int
    {
        $updated = User::whereIn('id', $userIds)->update($data);
        
        foreach ($userIds as $userId) {
            $this->clearUserCache($userId);
        }
        
        return $updated;
    }
    
    /**
     * Implementation of abstract method
     */
    public function process(array $data): bool
    {
        // Implementation specific to user processing
        return $this->validateUserData($data);
    }
    
    /**
     * Send verification email to user
     */
    private function sendVerificationEmail(User $user): void
    {
        Mail::to($user->email)->send(new \App\Mail\EmailVerification($user));
    }
    
    /**
     * Update user's last login timestamp
     */
    private function updateLastLogin(User $user): void
    {
        $user->update(['last_login_at' => now()]);
    }
    
    /**
     * Validate user data
     */
    private function validateUserData(array $data): bool
    {
        $required = ['name', 'email', 'password'];
        
        foreach ($required as $field) {
            if (!isset($data[$field]) || empty($data[$field])) {
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * Clear user from cache
     */
    protected function clearUserCache(int $userId): void
    {
        $this->forget("user:{$userId}");
    }
}

/**
 * Interface for user service contract
 */
interface UserServiceContract
{
    public function createUser(array $userData): User;
    public function updateUser(User $user, array $data): bool;
}

/**
 * Trait for common user operations
 */
trait UserOperations
{
    /**
     * Format user display name
     */
    public function formatDisplayName(User $user): string
    {
        return $user->first_name . ' ' . $user->last_name;
    }
    
    /**
     * Check if user is active
     */
    public function isUserActive(User $user): bool
    {
        return $user->status === User::STATUS_ACTIVE;
    }
}