package rl.collab.diabeat

import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

// ends with '/'
interface Api {
    @POST("/api/register/")
    suspend fun register(@Body obj: Request.Register)
            : Response<Result.Tokens>

    @POST("/api/token/")
    suspend fun logIn(@Body obj: Request.Login)
            : Response<Result.Tokens>

    @POST("/api/token/refresh/")
    suspend fun refresh(@Body obj: Request.Refresh)
            : Response<Result.Refresh>

    @POST("/api/auth/google/")
    suspend fun googleSignIn(@Body obj: Request.GoogleSignIn)
            : Response<Map<String, Any?>>

    @GET("/api/records/")
    suspend fun getRecords(@Header("Authorization") token: String)
            : Response<List<Result.Records>>

    @POST("/api/records/")
    suspend fun postRecord(@Header("Authorization") token: String, @Body obj: Request.Record)
            : Response<Result.Records>

    @Multipart
    @POST("/api/predict/")
    suspend fun predictCarbohydrate(@Header("Authorization") token: String, @Part image: MultipartBody.Part)
            : Response<Result.Predict>

    @GET("/api/chat/")
    suspend fun suggest(@Header("Authorization") token: String)
            : Response<Result.ChatRoot>

    @POST("/api/predictform/")
    suspend fun predictDiabetes(@Header("Authorization") token: String, @Body obj: Request.Diabetes)
            : Response<Result.Diabetes>
}

object Request {
    data class Register(
        val email: String,
        val username: String,
        val password: String
    )

    data class Login(
        val username_or_email: String,
        val password: String
    )

    data class Refresh(
        val refresh: String
    )

    data class GoogleSignIn(
        val code: String
    )

    data class Record(
        val blood_glucose: Double,
        val carbohydrate_intake: Double?,
        val exercise_duration: Double?,
        val insulin_injection: Double?
    )

    data class Diabetes(
        val gender: String,
        val age: Int,
        val hypertension: Boolean,
        val heart_disease: Boolean,
        val smoking_history: String,
        val bmi: Double,
        val HbA1c_level: Double,
        val blood_glucose_level: Int
    )
}

object Result {
    data class Tokens(
        val access: String,
        val refresh: String,
        val message: String,
        val success: Boolean
    )

    data class Refresh(
        val access: String,
        val refresh: String,
        val username: String,
        val message: String,
        val success: Boolean
    )

    data class Records(
        val id: Int,
        val user: Int,
        val blood_glucose: Double,
        val carbohydrate_intake: Double?,
        val exercise_duration: Double?,
        val insulin_injection: Double?,
        val created_at: String,
        val time_slot: String
    )

    data class Predict(
        val predicted_value: Double
    )

    data class ChatRoot(
        val response: Chat
    )

    data class Chat(
        val model: String,
        val created_at: String,
        val done: Boolean,
        val done_reason: String,
        val total_duration: Long,
        val load_duration: Long,
        val prompt_evalCount: Int,
        val prompt_eval_duration: Long,
        val eval_count: Int,
        val eval_duration: Long,
        val message: ChatMsg
    )

    data class ChatMsg(
        val role: String,
        val content: String,
        val images: String?,
        val tool_calls: String?
    )

    data class Diabetes(
        val prediction: Int
    )
}

object Err {
    data class Register(
        var email: List<String>?,
        var username: List<String>?,
    )

    data class Login(
        val non_field_errors: List<String>
    )
}