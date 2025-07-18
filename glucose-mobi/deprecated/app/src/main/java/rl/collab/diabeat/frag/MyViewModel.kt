package rl.collab.diabeat.frag

import android.app.Activity
import android.content.SharedPreferences
import android.text.Editable
import androidx.core.widget.doAfterTextChanged
import androidx.lifecycle.ViewModel
import com.google.gson.Gson
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import rl.collab.diabeat.Api
import rl.collab.diabeat.Result
import rl.collab.diabeat.databinding.DiaHostBinding
import rl.collab.diabeat.dialog
import rl.collab.diabeat.pos
import rl.collab.diabeat.str
import rl.collab.diabeat.syncEdit
import rl.collab.diabeat.toast
import java.util.concurrent.TimeUnit

class MyViewModel : ViewModel() {
    lateinit var remePref: SharedPreferences
    lateinit var hostPref: SharedPreferences
    val hostStartup get() = hostPref.getBoolean("startup", true)
    val hostAddr get() = hostPref.getString("addr", "192.168.0.0")!!

    lateinit var addr: String
    lateinit var retro: Lazy<Api>
    lateinit var retroLong: Lazy<Api>

    var acc: String? = null
    var access: String? = null
    var refresh: String? = null
    val records = mutableListOf<Result.Records>()

    fun resetRetro(pAddr: String) {
        fun retroInit(isLong: Boolean): Api {
            val okHttpClient = OkHttpClient.Builder()
                .connectTimeout(3, TimeUnit.SECONDS)
                .writeTimeout(3, TimeUnit.SECONDS)
                .readTimeout(if (isLong) 60 else 3, TimeUnit.SECONDS)
                .build()

            return Retrofit.Builder()
                .addConverterFactory(GsonConverterFactory.create(Gson()))
                .baseUrl("http://$addr:8000/")
                .client(okHttpClient)
                .build()
                .create(Api::class.java)
        }

        addr = pAddr
        retro = lazy { retroInit(false) }
        retroLong = lazy { retroInit(true) }
    }

    fun setHost(act: Activity) {
        val b1 = DiaHostBinding.inflate(act.layoutInflater)
        b1.apply {
            startUpCb.isChecked = hostStartup

            val ets = arrayOf(hostA, hostB, hostC, hostD)
            val dialog = act.dialog("Host 設定", view = root)
            val posBtn = dialog.pos
            posBtn.setOnClickListener {
                act.toast("修改完成✅")
                dialog.dismiss()

                val addr = ets.joinToString(".") { it.str }
                hostPref.syncEdit {
                    putBoolean("startup", startUpCb.isChecked)
                    putString("addr", addr)
                }
                resetRetro(addr)
            }

            val parts = hostAddr.split('.')
            val watcher = { _: Editable? ->
                posBtn.isEnabled = ets.all { it.str.isNotEmpty() && it.str.toInt() <= 255 }
            }
            for (i in 0..3)
                ets[i].apply {
                    str = parts[i]
                    doAfterTextChanged(watcher)
                }
            hostD.setOnEditorActionListener { _, _, _ ->
                posBtn.callOnClick()
            }
        }
    }

    fun logInEnv(pAcc: String, pAccessRaw: String, pRefresh: String, reme: Boolean?) {
        acc = pAcc
        access = "Bearer $pAccessRaw"
        refresh = pRefresh

        reme ?: return
        remePref.syncEdit {
            if (reme)
                putString("acc", acc)
            else
                clear()
        }
    }
}