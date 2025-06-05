<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/**
 * User model representing application users
 * 
 * @property int $id
 * @property string $name
 * @property string $email
 * @property string $password
 */
class User extends Model
{
    use HasFactory;
    
    /**
     * The attributes that are mass assignable.
     */
    protected array $fillable = [
        'name',
        'email',
        'password',
    ];
    
    /**
     * The attributes that should be hidden for serialization.
     */
    protected array $hidden = [
        'password',
        'remember_token',
    ];
    
    /**
     * The attributes that should be cast.
     */
    protected array $casts = [
        'email_verified_at' => 'datetime',
        'password' => 'hashed',
    ];
    
    // Constants
    public const STATUS_ACTIVE = 'active';
    public const STATUS_INACTIVE = 'inactive';
    private const MAX_LOGIN_ATTEMPTS = 5;
    
    /**
     * Get the posts for the user.
     */
    public function posts(): HasMany
    {
        return $this->hasMany(Post::class);
    }
    
    /**
     * Get the profile for the user.
     */
    public function profile(): BelongsTo
    {
        return $this->belongsTo(Profile::class);
    }
    
    /**
     * Get the user's full name.
     */
    public function getFullNameAttribute(): string
    {
        return $this->first_name . ' ' . $this->last_name;
    }
    
    /**
     * Check if user is admin.
     */
    public function isAdmin(): bool
    {
        return $this->role === 'admin';
    }
    
    /**
     * Find user by email or username.
     */
    public static function findByEmailOrUsername(string $identifier): ?self
    {
        return static::where('email', $identifier)
            ->orWhere('username', $identifier)
            ->first();
    }
    
    /**
     * Scope a query to only include active users.
     */
    public function scopeActive($query)
    {
        return $query->where('status', self::STATUS_ACTIVE);
    }
    
    /**
     * Hash the password when setting it.
     */
    protected function setPasswordAttribute(string $password): void
    {
        $this->attributes['password'] = bcrypt($password);
    }
    
    /**
     * Private method to normalize email.
     */
    private function normalizeEmail(): void
    {
        $this->email = strtolower(trim($this->email));
    }
    
    /**
     * Protected method to check permissions.
     */
    protected function canEdit(User $user): bool
    {
        return $user->id === $this->id || $user->isAdmin();
    }
}