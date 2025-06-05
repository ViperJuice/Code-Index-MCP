package controllers

import javax.inject._
import play.api._
import play.api.mvc._
import play.api.libs.json._
import play.api.libs.functional.syntax._
import scala.concurrent.{Future, ExecutionContext}
import models._
import services._

// Model case classes
case class User(id: Long, email: String, name: String, role: String)
case class CreateUserRequest(email: String, name: String, password: String)
case class UpdateUserRequest(name: Option[String], role: Option[String])
case class LoginRequest(email: String, password: String)
case class AuthToken(token: String, expiresIn: Long)

// JSON formatters
object JsonFormats {
  implicit val userFormat: Format[User] = Json.format[User]
  implicit val createUserFormat: Format[CreateUserRequest] = Json.format[CreateUserRequest]
  implicit val updateUserFormat: Format[UpdateUserRequest] = Json.format[UpdateUserRequest]
  implicit val loginFormat: Format[LoginRequest] = Json.format[LoginRequest]
  implicit val authTokenFormat: Format[AuthToken] = Json.format[AuthToken]
  
  // Custom reads with validation
  implicit val emailReads: Reads[String] = Reads.email
  
  implicit val validatedUserReads: Reads[CreateUserRequest] = (
    (JsPath \ "email").read[String](emailReads) and
    (JsPath \ "name").read[String](minLength[String](2)) and
    (JsPath \ "password").read[String](minLength[String](8))
  )(CreateUserRequest.apply _)
}

// Custom action builders
class AuthenticatedRequest[A](val user: User, request: Request[A]) 
  extends WrappedRequest[A](request)

@Singleton
class AuthAction @Inject()(
  val parser: BodyParsers.Default,
  authService: AuthService
)(implicit val executionContext: ExecutionContext) 
  extends ActionBuilder[AuthenticatedRequest, AnyContent] {
  
  override def invokeBlock[A](
    request: Request[A], 
    block: AuthenticatedRequest[A] => Future[Result]
  ): Future[Result] = {
    request.headers.get("Authorization") match {
      case Some(token) =>
        authService.validateToken(token).flatMap {
          case Some(user) => block(new AuthenticatedRequest(user, request))
          case None => Future.successful(Results.Unauthorized("Invalid token"))
        }
      case None =>
        Future.successful(Results.Unauthorized("Missing Authorization header"))
    }
  }
}

// Main controller
@Singleton
class UserController @Inject()(
  val controllerComponents: ControllerComponents,
  userService: UserService,
  authService: AuthService,
  authAction: AuthAction
)(implicit ec: ExecutionContext) extends BaseController {
  
  import JsonFormats._
  
  // Public endpoints
  def register: Action[JsValue] = Action.async(parse.json) { implicit request =>
    request.body.validate[CreateUserRequest] match {
      case JsSuccess(userData, _) =>
        userService.createUser(userData).map { user =>
          Created(Json.toJson(user))
        }.recover {
          case e: DuplicateEmailException =>
            Conflict(Json.obj("error" -> "Email already exists"))
          case e: Exception =>
            InternalServerError(Json.obj("error" -> e.getMessage))
        }
      
      case JsError(errors) =>
        Future.successful(
          BadRequest(Json.obj("errors" -> JsError.toJson(errors)))
        )
    }
  }
  
  def login: Action[JsValue] = Action.async(parse.json) { implicit request =>
    request.body.validate[LoginRequest] match {
      case JsSuccess(loginData, _) =>
        authService.authenticate(loginData.email, loginData.password).map {
          case Some(token) => Ok(Json.toJson(token))
          case None => Unauthorized(Json.obj("error" -> "Invalid credentials"))
        }
      
      case JsError(errors) =>
        Future.successful(
          BadRequest(Json.obj("errors" -> JsError.toJson(errors)))
        )
    }
  }
  
  // Protected endpoints
  def getUser(id: Long): Action[AnyContent] = authAction.async { implicit request =>
    userService.findById(id).map {
      case Some(user) => Ok(Json.toJson(user))
      case None => NotFound(Json.obj("error" -> "User not found"))
    }
  }
  
  def updateUser(id: Long): Action[JsValue] = authAction.async(parse.json) { implicit request =>
    // Authorization check
    if (request.user.id != id && request.user.role != "admin") {
      Future.successful(Forbidden(Json.obj("error" -> "Access denied")))
    } else {
      request.body.validate[UpdateUserRequest] match {
        case JsSuccess(updateData, _) =>
          userService.updateUser(id, updateData).map {
            case Some(user) => Ok(Json.toJson(user))
            case None => NotFound(Json.obj("error" -> "User not found"))
          }
        
        case JsError(errors) =>
          Future.successful(
            BadRequest(Json.obj("errors" -> JsError.toJson(errors)))
          )
      }
    }
  }
  
  def deleteUser(id: Long): Action[AnyContent] = authAction.async { implicit request =>
    if (request.user.role != "admin") {
      Future.successful(Forbidden(Json.obj("error" -> "Admin access required")))
    } else {
      userService.deleteUser(id).map { deleted =>
        if (deleted) NoContent
        else NotFound(Json.obj("error" -> "User not found"))
      }
    }
  }
  
  def listUsers(page: Int, pageSize: Int): Action[AnyContent] = authAction.async { implicit request =>
    userService.listUsers(page, pageSize).map { case (users, total) =>
      Ok(Json.obj(
        "users" -> users,
        "pagination" -> Json.obj(
          "page" -> page,
          "pageSize" -> pageSize,
          "total" -> total,
          "totalPages" -> Math.ceil(total.toDouble / pageSize).toInt
        )
      ))
    }
  }
  
  // File upload
  def uploadAvatar(id: Long): Action[MultipartFormData[Files.TemporaryFile]] = 
    authAction.async(parse.multipartFormData) { implicit request =>
      if (request.user.id != id) {
        Future.successful(Forbidden(Json.obj("error" -> "Can only upload own avatar")))
      } else {
        request.body.file("avatar") match {
          case Some(file) =>
            userService.updateAvatar(id, file).map { avatarUrl =>
              Ok(Json.obj("avatarUrl" -> avatarUrl))
            }
          case None =>
            Future.successful(
              BadRequest(Json.obj("error" -> "Missing file"))
            )
        }
      }
    }
  
  // WebSocket endpoint
  def userEvents: WebSocket = WebSocket.acceptOrResult[JsValue, JsValue] { request =>
    request.headers.get("Authorization") match {
      case Some(token) =>
        authService.validateToken(token).map {
          case Some(user) =>
            Right(ActorFlow.actorRef { out =>
              UserWebSocketActor.props(out, user)
            })
          case None =>
            Left(Unauthorized("Invalid token"))
        }
      case None =>
        Future.successful(Left(Unauthorized("Missing Authorization header")))
    }
  }
}

// Action composition
trait SecuredController extends BaseController {
  def authAction: AuthAction
  
  def withRole(role: String) = new ActionBuilder[AuthenticatedRequest, AnyContent] {
    override def parser = authAction.parser
    override def executionContext = authAction.executionContext
    
    override def invokeBlock[A](
      request: Request[A], 
      block: AuthenticatedRequest[A] => Future[Result]
    ): Future[Result] = {
      authAction.invokeBlock(request, { authRequest =>
        if (authRequest.user.role == role) {
          block(authRequest)
        } else {
          Future.successful(Forbidden("Insufficient permissions"))
        }
      })
    }
  }
  
  def AdminAction = withRole("admin")
  def UserAction = authAction
}

// Filters
@Singleton
class LoggingFilter @Inject()(implicit val mat: Materializer, ec: ExecutionContext) 
  extends Filter {
  
  def apply(nextFilter: RequestHeader => Future[Result])
           (requestHeader: RequestHeader): Future[Result] = {
    val startTime = System.currentTimeMillis
    
    nextFilter(requestHeader).map { result =>
      val requestTime = System.currentTimeMillis - startTime
      Logger.info(s"${requestHeader.method} ${requestHeader.uri} " +
        s"took ${requestTime}ms and returned ${result.header.status}")
      result.withHeaders("Request-Time" -> requestTime.toString)
    }
  }
}