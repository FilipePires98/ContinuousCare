<template>
    <section class="home_banner_area">
        <div class="banner_inner d-flex align-items-center">
            <div class="container">
                <div class="banner_content row">
                    <div class="col-lg-12">
                        <h1>ContinuousCare</h1>
                        <p>Our Health Monitoring System aims to aid users to keep track of their health status and help medical personel to make better decisions.</p>
                        <nuxt-link class="main_btn mr-10" to="/register">register</nuxt-link>
                    </div>
                </div>
            </div>
        </div>
        <nuxt/>
    </section>
</template>

<script>
export default {
    name: 'HomeBanner',
    props: {

    }
}
</script>

<style>

</style>
