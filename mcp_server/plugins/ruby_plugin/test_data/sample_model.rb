# Sample ActiveRecord model for testing
class User < ApplicationRecord
  # Associations
  has_many :posts, dependent: :destroy
  has_one :profile
  belongs_to :organization, optional: true
  
  # Validations
  validates :email, presence: true, uniqueness: true
  validates :name, presence: true, length: { minimum: 2 }
  
  # Scopes
  scope :active, -> { where(active: true) }
  scope :recent, -> { where('created_at > ?', 1.week.ago) }
  
  # Class methods
  def self.find_by_email_or_username(identifier)
    where('email = ? OR username = ?', identifier, identifier).first
  end
  
  # Instance methods
  def full_name
    "#{first_name} #{last_name}"
  end
  
  def admin?
    role == 'admin'
  end
  
  # Private methods
  private
  
  def normalize_email
    self.email = email.downcase.strip
  end
  
  protected
  
  def can_edit?(user)
    user == self || user.admin?
  end
end