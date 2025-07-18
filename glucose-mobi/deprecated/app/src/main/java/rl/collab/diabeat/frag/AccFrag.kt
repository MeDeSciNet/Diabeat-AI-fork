package rl.collab.diabeat.frag

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.text.Editable
import android.util.Patterns
import android.view.View
import android.view.inputmethod.InputMethodManager
import androidx.appcompat.app.AlertDialog
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_WEAK
import androidx.biometric.BiometricManager.BIOMETRIC_SUCCESS
import androidx.biometric.BiometricPrompt
import androidx.core.widget.doAfterTextChanged
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.gson.Gson
import io.noties.markwon.Markwon
import kotlinx.coroutines.cancelChildren
import kotlinx.coroutines.delay
import rl.collab.diabeat.Err
import rl.collab.diabeat.R
import rl.collab.diabeat.Request
import rl.collab.diabeat.Result
import rl.collab.diabeat.databinding.DiaDiabetesInBinding
import rl.collab.diabeat.databinding.DiaDiabetesOutBinding
import rl.collab.diabeat.databinding.DiaLoginBinding
import rl.collab.diabeat.databinding.DiaRegisterBinding
import rl.collab.diabeat.databinding.FragAccBinding
import rl.collab.diabeat.nacho
import rl.collab.diabeat.neu
import rl.collab.diabeat.pos
import rl.collab.diabeat.str
import rl.collab.diabeat.syncEdit
import java.util.concurrent.atomic.AtomicBoolean

class AccFrag : MyFrag<FragAccBinding>(FragAccBinding::inflate) {
    private val notLoginView get() = binding.profileLy.visibility != View.VISIBLE

    private val remeAcc get() = vm.remePref.getString("acc", null)
    private val remeRefresh get() = vm.remePref.getString("refresh", null)
    private val remeCanBio get() = remeRefresh != null
    private val remeStrong get() = vm.remePref.getBoolean("strong", false)

    private val canBio
        get() = BiometricManager.from(con).canAuthenticate(BIOMETRIC_WEAK) == BIOMETRIC_SUCCESS
    private val canStrongBio
        get() = BiometricManager.from(con).canAuthenticate(BIOMETRIC_STRONG) == BIOMETRIC_SUCCESS

    override fun FragAccBinding.setView() {
        googleSignInBtn.setOnClickListener { googleSignIn() }
        registerBtn.setOnClickListener {
            rq(DiaRegisterBinding::inflate) { register() }
        }
        loginBtn.setOnClickListener {
            rq(DiaLoginBinding::inflate) { logIn() }
        }
        aboutUsBtn.setOnClickListener {
            val uri = Uri.parse("https://github.com/creaper9487/2025-AI-glucose")
            startActivity(Intent(Intent.ACTION_VIEW, uri))
        }

        suggestBtn.setOnClickListener { suggest() }
        predictDiabetesBtn.setOnClickListener {
            rq(DiaDiabetesInBinding::inflate) { predictDiabetes() }
        }
        logOutBtn.setOnClickListener { logOutEnv() }
        bioLoginSw.setOnCheckedChangeListener { _, isChecked ->
            if (notLoginView)
                return@setOnCheckedChangeListener

            vm.remePref.syncEdit {
                if (isChecked) {
                    strongBioSw.isEnabled = canStrongBio
                    putString("acc", vm.acc)
                    putString("refresh", vm.refresh)
                } else {
                    strongBioSw.isEnabled = false
                    clear()
                }
                strongBioSw.isChecked = false
                strongBioSw.jumpDrawablesToCurrentState()
            }
        }
        strongBioSw.setOnCheckedChangeListener { _, isChecked ->
            if (notLoginView)
                return@setOnCheckedChangeListener

            vm.remePref.syncEdit {
                if (isChecked)
                    putBoolean("strong", true)
                else
                    remove("strong")
            }
        }
        vm.acc?.also { logInView() } ?: logOutEnv()
    }

    private fun FragAccBinding.logInView() {
        accLy.visibility = View.INVISIBLE
        profileLy.visibility = View.VISIBLE
        profileTv.text = "Hi, ${vm.acc}"

        if (canStrongBio) {
            bioLoginSw.isEnabled = true
            bioLoginSw.isChecked = remeCanBio

            strongBioSw.isEnabled = remeCanBio
            strongBioSw.isChecked = remeCanBio && remeStrong
        } else if (canBio) {
            bioLoginSw.isEnabled = true
            bioLoginSw.isChecked = remeCanBio

            strongBioSw.isEnabled = false
            strongBioSw.isChecked = false
        } else {
            bioLoginSw.isEnabled = false
            bioLoginSw.isChecked = false

            strongBioSw.isEnabled = false
            strongBioSw.isChecked = false
        }
        bioLoginSw.jumpDrawablesToCurrentState()
        strongBioSw.jumpDrawablesToCurrentState()
    }

    private fun logOutEnv() {
        vm.acc = null
        vm.access = null
        vm.refresh = null
        vm.records.clear()
        binding.profileLy.visibility = View.INVISIBLE
        binding.accLy.visibility = View.VISIBLE
    }

    private fun share(content: String) {
        val intent = Intent(Intent.ACTION_SEND).apply {
            putExtra(Intent.EXTRA_TEXT, content)
            type = "text/plain"
        }
        startActivity(Intent.createChooser(intent, null))
    }

    //
    //
    // Request

    private fun reqDialog(
        title: String,
        msg: String? = null,
        view: View? = null,
        pos: String? = "OK",
        neg: String? = "取消",
        neutral: String? = null,
    ): AlertDialog {
        val dialog = dialog(title, msg, view, pos, neg, neutral)
        dialog.setOnDismissListener {
            viewLifecycleScope.coroutineContext.cancelChildren()
        }
        return dialog
    }

    private fun googleSignIn() {
        val opt = GetGoogleIdOption.Builder()
            .setFilterByAuthorizedAccounts(false)
            .setServerClientId(getString(R.string.token))
            .build()

        val credentialObj = GetCredentialRequest.Builder()
            .addCredentialOption(opt)
            .build()

        launch {
            try {
                val credential = CredentialManager.create(con)
                    .getCredential(con, credentialObj)
                    .credential

                if (credential !is CustomCredential ||
                    credential.type != GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL
                ) {
                    toast("無法獲取有效憑證")
                    return@launch
                }

                val googleIdTokenCredential = GoogleIdTokenCredential.createFrom(credential.data)
                // val email = googleIdTokenCredential.id
                val idToken = googleIdTokenCredential.idToken
                // val name = googleIdTokenCredential.displayName

                val obj = Request.GoogleSignIn(idToken)
                val onSucceed = { r: Map<String, Any?> ->
                    nacho(r)
                    dialog("nig", r.toString())
                    Unit
                }
                request(onSucceed, null, null, false) { googleSignIn(obj) }

            } catch (_: GetCredentialCancellationException) {
            } catch (e: NoCredentialException) {
                errDialog("沒有找到可用的憑證")
            } catch (e: Exception) {
                exceptionDialog(e)
            }
        }
    }

    private fun DiaRegisterBinding.register() {
        val dialog = reqDialog("註冊", view = root)
        val pos = dialog.pos

        pos.isEnabled = false
        pos.setOnClickListener {
            pos.isEnabled = false

            val obj = Request.Register(emailEt.str, usernameEt.str, pwEt.str)
            val onSucceed = { r: Result.Tokens ->
                dialog.dismiss()
                vm.logInEnv(obj.username, r.access, r.refresh, false)
                binding.logInView()
            }
            val onBadRequest = { str: String? ->
                val err = Gson().fromJson(str, Err.Register::class.java)
                if (err.email != null && err.username != null)
                    "此 Email 和 Username 皆已被註冊"
                else if (err.email != null)
                    "此 Email 已被註冊"
                else
                    "此 Username 已被註冊"
            }
            val onFail = {
                dialog.pos.isEnabled = true
            }
            request(onSucceed, onBadRequest, onFail, false) { register(obj) }
        }
        val watcher = { _: Editable? ->
            pos.isEnabled = Patterns.EMAIL_ADDRESS.matcher(emailEt.str).matches() &&
                    usernameEt.str.isNotEmpty() &&
                    pwEt.str.isNotEmpty()
        }
        emailEt.doAfterTextChanged(watcher)
        usernameEt.doAfterTextChanged(watcher)
        pwEt.doAfterTextChanged(watcher)
    }

    private fun DiaLoginBinding.logIn() {
        remeAcc?.also {
            accEt.str = it
            remeCb.isChecked = true
        }

        val dialog = dialog("登入", view = root, neutral = "生物辨識")
        val pos = dialog.pos
        val neu = dialog.neu

        fun posWatcher() {
            pos.isEnabled = accEt.str.isNotEmpty() && pwEt.str.isNotEmpty()
        }

        fun enableDiaBtns(b: Boolean) {
            if (b) {
                posWatcher()
                neu.isEnabled = remeCanBio
            } else {
                pos.isEnabled = false
                neu.isEnabled = false
            }
        }

        pos.setOnClickListener {
            enableDiaBtns(false)

            val obj = Request.Login(accEt.str.trim(), pwEt.str)
            val onSucceed = { r: Result.Tokens ->
                dialog.dismiss()
                vm.logInEnv(obj.username_or_email, r.access, r.refresh, remeCb.isChecked)
                binding.logInView()
            }
            val onBadRequest = { str: String? ->
                val err = Gson().fromJson(str, Err.Login::class.java)
                when (err.non_field_errors[0]) {
                    "Email does not exist." -> "Email 不存在"
                    "Username does not exist." -> "Username 不存在"
                    "Incorrect password." -> "密碼錯誤"
                    else -> "登入失敗"
                }
            }
            val onFail = {
                enableDiaBtns(true)
            }
            request(onSucceed, onBadRequest, onFail, false) { logIn(obj) }
        }
        neu.setOnClickListener { _ ->
            enableDiaBtns(false)

            val addOnSucceed = { it: Result.Refresh ->
                dialog.dismiss()
                vm.logInEnv(it.username, it.access, it.refresh, remeCb.isChecked)
                binding.logInView()
            }
            val promptInfo = BiometricPrompt.PromptInfo.Builder()
                .setTitle("生物辨識登入")
                .setNegativeButtonText("取消")
                .setAllowedAuthenticators(if (remeStrong) BIOMETRIC_STRONG else BIOMETRIC_WEAK)
                .build()
            val callback = object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    refresh(remeRefresh, addOnSucceed) { enableDiaBtns(true) }
                }

                override fun onAuthenticationFailed() {
                    super.onAuthenticationFailed()
                    enableDiaBtns(true)
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    enableDiaBtns(true)
                }
            }
            BiometricPrompt(this@AccFrag, callback).authenticate(promptInfo)
        }
        accEt.doAfterTextChanged { posWatcher() }
        pwEt.doAfterTextChanged { posWatcher() }
        pwEt.setOnEditorActionListener { _, _, _ ->
            val imm = con.getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
            imm.hideSoftInputFromWindow(pwEt.windowToken, 0)
            pos.callOnClick()
        }

        enableDiaBtns(true)
        if (neu.isEnabled)
            neu.callOnClick()
    }

    private fun suggest() {
        val atomic = AtomicBoolean(false)
        var res: Result.Chat? = null
        val onSucceed = { r: Result.ChatRoot ->
            res = r.response
            atomic.set(true)
        }
        request(onSucceed, null, null, true) { suggest(vm.access!!) }

        val dialog = reqDialog("AI 建議", "耐心等待6️⃣0️⃣秒", pos = "取消", neg = null, neutral = " ")
        launch {
            val nums = arrayOf("0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣")

            for (i in 60 downTo 0) {
                if (atomic.get())
                    break

                val msg = "耐心等待${nums[i / 10]}${nums[i % 10]}秒\n\n" +
                        i.toString(2).replace("0", "🌑").replace("1", "🌕")

                dialog.setMessage(msg)
                delay(1000)
            }
            if (!atomic.get())
                return@launch

            val content = res!!.message.content
            val spannedString = Markwon.create(con).toMarkdown(content)

            dialog.setTitle("${res!!.model} 建議")
            dialog.setMessage(spannedString)
            dialog.pos.text = "OK"
            dialog.neu.apply {
                text = "分享"
                setOnClickListener { share(content) }
            }
        }
    }

    private fun DiaDiabetesInBinding.predictDiabetes() {
        val ets = arrayOf(smokingHistoryAc, ageEt, bmiEt, hb1acEt, glucoseEt)
        val simpleItems = arrayOf("從不吸菸", "曾經吸菸", "目前沒有吸菸", "目前有吸菸")
        val objItems = arrayOf("never", "former", "not current", "current")
        smokingHistoryAc.setSimpleItems(simpleItems)

        val dialog = reqDialog("預測是否有糖尿病", view = root)
        val pos = dialog.pos
        pos.isEnabled = false
        pos.setOnClickListener {
            val obj = Request.Diabetes(
                if (maleRb.isChecked) "male" else "female",
                ageEt.str.toInt(),
                hypertensionCb.isChecked,
                heartDiseaseCb.isChecked,
                objItems[simpleItems.indexOf(smokingHistoryAc.str)],
                bmiEt.str.toDouble(),
                hb1acEt.str.toDouble(),
                glucoseEt.str.toInt()
            )

            val onSucceed = { r: Result.Diabetes ->
                dialog.dismiss()
                val isDiagnosed = r.prediction == 1

                val b2Root = rq(DiaDiabetesOutBinding::inflate) {
                    if (isDiagnosed) {
                        iv.setImageResource(R.drawable.exclamation_mark)
                        tv.text = "是\n\n本預測僅供參考，請務必諮詢專業醫護人員"
                    } else {
                        iv.setImageResource(R.drawable.check)
                        tv.text = "否\n\n本預測僅供參考，請務必諮詢專業醫護人員"
                    }
                }.root

                val disease =
                    if (obj.hypertension && obj.heart_disease) "高血壓、心臟病"
                    else if (obj.hypertension) "高血壓"
                    else if (obj.heart_disease) "心臟病"
                    else "無"

                val content = "性別：${if (obj.gender == "male") "男" else "女"}\n" +
                        "疾病史：$disease\n" +
                        "吸菸史：${simpleItems[objItems.indexOf(obj.smoking_history)]}\n" +
                        "年齡：${obj.age}\n" +
                        "BMI：${obj.bmi}\n" +
                        "Hb1Ac值：${obj.HbA1c_level}\n" +
                        "血糖值：${obj.blood_glucose_level}\n\n" +
                        "預測結果：${if (isDiagnosed) "是" else "否"}"

                dialog("預測結果", view = b2Root, neg = null, neutral = "分享").neu.setOnClickListener {
                    share(content)
                }
            }

            request(onSucceed, null, null, false) { predictDiabetes(vm.access!!, obj) }
        }
        fun watcher() {
            pos.isEnabled = genderRg.checkedRadioButtonId != -1 && ets.all { it.str.isNotEmpty() }
        }
        genderRg.setOnCheckedChangeListener { _, _ -> watcher() }
        for (et in ets)
            et.doAfterTextChanged { watcher() }
    }
}